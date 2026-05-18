from __future__ import annotations
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from .decorators import handle_errors, timer
from .models import Transaction
from .service import LedgerService


# ── Validation helpers ───────────────────────────────────────────────────────

def _validate_date(s: str) -> str:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        raise ValueError(
            "날짜 형식이 올바르지 않습니다.\n[힌트] 예: 2024-01-15 (YYYY-MM-DD)"
        )


def _validate_type(s: str) -> str:
    if s not in ("income", "expense"):
        raise ValueError(
            "타입이 올바르지 않습니다.\n[힌트] income 또는 expense 중 하나를 입력하세요."
        )
    return s


def _validate_amount(s: str) -> int:
    try:
        v = int(s)
    except ValueError:
        raise ValueError("금액은 정수여야 합니다.\n[힌트] 예: 15000")
    if v <= 0:
        raise ValueError("금액은 양수여야 합니다.\n[힌트] 0보다 큰 정수를 입력하세요.")
    return v


def _validate_month(s: str) -> str:
    try:
        datetime.strptime(s, "%Y-%m")
        return s
    except ValueError:
        raise ValueError(
            "월 형식이 올바르지 않습니다.\n[힌트] 예: 2024-01 (YYYY-MM)"
        )


# ── Display helpers ──────────────────────────────────────────────────────────

def _fmt_tx(tx: Transaction) -> str:
    tags = f"[{','.join(tx.tags)}]" if tx.tags else ""
    return (
        f"{tx.id} | {tx.date} | {tx.type:<7} | {tx.category:<15} | "
        f"{tx.amount:>10,} | {tx.memo:<20} {tags}"
    ).rstrip()


def _prompt(label: str) -> str:
    return input(f"{label}: ").strip()


# ── Command handlers ─────────────────────────────────────────────────────────

@handle_errors
def cmd_add(svc: LedgerService, _args: argparse.Namespace) -> None:
    print("거래를 추가합니다. (Ctrl+C로 취소)")

    while True:
        raw = _prompt("날짜(YYYY-MM-DD)")
        try:
            date_ = _validate_date(raw)
            break
        except ValueError as e:
            print(f"[오류] {e}")

    while True:
        raw = _prompt("타입(income/expense)")
        try:
            type_ = _validate_type(raw)
            break
        except ValueError as e:
            print(f"[오류] {e}")

    cats = svc.list_categories()
    print(f"  카테고리: {', '.join(cats)}")
    while True:
        category = _prompt("카테고리")
        if svc.category_exists(category):
            break
        print(f"[오류] '{category}'는 등록되지 않은 카테고리입니다.")
        yn = _prompt("  새로 추가하시겠습니까? (y/n)").lower()
        if yn == "y":
            svc.add_category(category)
            print(f"[안내] '{category}' 카테고리가 추가됐습니다.")
            break

    while True:
        raw = _prompt("금액(양수 정수)")
        try:
            amount = _validate_amount(raw)
            break
        except ValueError as e:
            print(f"[오류] {e}")

    memo = _prompt("메모(선택, 없으면 엔터)")
    tags_raw = _prompt("태그(쉼표 구분, 없으면 엔터)")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    tx = svc.add_transaction(type_=type_, date_=date_, amount=amount,
                             category=category, memo=memo, tags=tags)
    print(f"[저장 완료] id={tx.id}")


@handle_errors
@timer
def cmd_list(svc: LedgerService, args: argparse.Namespace) -> None:
    results = sorted(svc.stream_all(), key=lambda t: t.date, reverse=True)
    shown = results[:args.limit]
    if not shown:
        print("거래 내역이 없습니다.")
        return
    for tx in shown:
        print(_fmt_tx(tx))
    if len(results) > args.limit:
        print(f"  ... (총 {len(results)}건 중 {args.limit}건 표시, --limit으로 조정)")


@handle_errors
@timer
def cmd_search(svc: LedgerService, args: argparse.Namespace) -> None:
    results = sorted(
        svc.search(
            from_date=args.from_date,
            to_date=args.to_date,
            category=args.category,
            type_=args.type,
            q=args.q,
            tag=args.tag,
        ),
        key=lambda t: t.date,
        reverse=True,
    )
    if not results:
        print("조건에 맞는 거래가 없습니다.")
        return
    for tx in results:
        print(_fmt_tx(tx))
    print(f"  총 {len(results)}건")


@handle_errors
def cmd_summary(svc: LedgerService, args: argparse.Namespace) -> None:
    try:
        _validate_month(args.month)
    except ValueError as e:
        print(f"[오류] {e}")
        raise SystemExit(1)

    s = svc.monthly_summary(args.month, top_n=args.top)
    if not s["has_data"]:
        print(f"[{args.month}] 해당 월의 거래 데이터가 없습니다.")
        return

    print(f"=== {args.month} 월별 요약 ===")
    print(f"총 수입: {s['income']:>12,}원")
    print(f"총 지출: {s['expense']:>12,}원")
    print(f"잔액  : {s['balance']:>12,}원")

    if s["budget"]:
        b = s["budget"]
        pct = s["expense"] / b.amount * 100 if b.amount else 0.0
        print(f"예산  : {b.amount:>12,}원 (사용률 {pct:.1f}%)")
        if s["expense"] > b.amount:
            over = s["expense"] - b.amount
            print(f"  [경고] 예산 초과! {over:,}원 초과 지출")

    if s["top_categories"]:
        print(f"\n지출 TOP {len(s['top_categories'])}")
        for i, (cat, amt) in enumerate(s["top_categories"], 1):
            print(f"  {i}) {cat:<15} {amt:>10,}원")


@handle_errors
def cmd_budget(svc: LedgerService, args: argparse.Namespace) -> None:
    action = args.budget_action
    if action == "set":
        try:
            _validate_month(args.month)
        except ValueError as e:
            print(f"[오류] {e}")
            raise SystemExit(1)
        svc.set_budget(args.month, args.amount)
        print(f"[저장 완료] {args.month} 예산 {args.amount:,}원")
    elif action == "get":
        b = svc.get_budget(args.month)
        if b:
            print(f"{args.month} 예산: {b.amount:,}원")
        else:
            print(f"[안내] {args.month}에 설정된 예산이 없습니다.")
    else:
        print("[오류] budget set 또는 budget get을 사용하세요.")
        raise SystemExit(1)


@handle_errors
def cmd_category(svc: LedgerService, args: argparse.Namespace) -> None:
    action = args.cat_action
    if action == "list":
        cats = svc.list_categories()
        if not cats:
            print("카테고리가 없습니다.")
        else:
            for c in cats:
                print(f"  - {c}")
    elif action == "add":
        name = _prompt("카테고리명").strip()
        if not name:
            print("[오류] 카테고리명을 입력하세요.")
            raise SystemExit(1)
        if svc.add_category(name):
            print(f"[저장 완료] category={name}")
        else:
            print(f"[안내] '{name}'은(는) 이미 존재하는 카테고리입니다.")
    elif action == "remove":
        name = _prompt("삭제할 카테고리명").strip()
        ok, msg = svc.remove_category(name)
        if ok:
            print(f"[삭제 완료] category={name}")
        else:
            print(f"[오류] {msg}")
            raise SystemExit(1)
    else:
        print("[오류] category list | add | remove 중 하나를 선택하세요.")
        raise SystemExit(1)


@handle_errors
def cmd_update(svc: LedgerService, args: argparse.Namespace) -> None:
    fields: dict = {}

    if args.date is not None:
        try:
            fields["date"] = _validate_date(args.date)
        except ValueError as e:
            print(f"[오류] {e}")
            raise SystemExit(1)

    if args.type is not None:
        try:
            fields["type"] = _validate_type(args.type)
        except ValueError as e:
            print(f"[오류] {e}")
            raise SystemExit(1)

    if args.category is not None:
        if not svc.category_exists(args.category):
            print(f"[오류] '{args.category}'는 등록되지 않은 카테고리입니다.")
            raise SystemExit(1)
        fields["category"] = args.category

    if args.amount is not None:
        try:
            fields["amount"] = _validate_amount(str(args.amount))
        except ValueError as e:
            print(f"[오류] {e}")
            raise SystemExit(1)

    if args.memo is not None:
        fields["memo"] = args.memo

    if args.tags is not None:
        fields["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]

    if not fields:
        print("[오류] 수정할 필드를 하나 이상 지정하세요.")
        print("[힌트] --date, --type, --category, --amount, --memo, --tags 중 선택")
        raise SystemExit(1)

    if svc.update_transaction(args.tx_id, **fields):
        print(f"[수정 완료] id={args.tx_id}")
    else:
        print(f"[오류] id='{args.tx_id}'를 찾을 수 없습니다.")
        raise SystemExit(1)


@handle_errors
def cmd_delete(svc: LedgerService, args: argparse.Namespace) -> None:
    if svc.delete_transaction(args.tx_id):
        print(f"[삭제 완료] id={args.tx_id}")
    else:
        print(f"[오류] id='{args.tx_id}'를 찾을 수 없습니다.")
        raise SystemExit(1)


@handle_errors
@timer
def cmd_import(svc: LedgerService, args: argparse.Namespace) -> None:
    if not Path(args.from_file).exists():
        print(f"[오류] 파일을 찾을 수 없습니다: {args.from_file}")
        print("[힌트] 경로와 파일명을 확인하세요.")
        raise SystemExit(1)
    imported, skipped = svc.import_csv(args.from_file)
    print(f"[완료] imported={imported}, skipped={skipped}")


@handle_errors
@timer
def cmd_export(svc: LedgerService, args: argparse.Namespace) -> None:
    if not args.month and not args.from_date and not args.to_date:
        print("[오류] --month 또는 --from/--to 조건이 필요합니다.")
        print("[힌트] 예: --month 2024-01  또는  --from 2024-01-01 --to 2024-01-31")
        raise SystemExit(1)
    count = svc.export_csv(
        out_path=args.out,
        from_date=args.from_date,
        to_date=args.to_date,
        month=args.month,
    )
    print(f"[완료] {args.out} ({count} records)")


@handle_errors
def cmd_backup(svc: LedgerService, _args: argparse.Namespace) -> None:
    dest = svc.backup()
    print(f"[백업 완료] {dest}")


# ── Argparse setup ───────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m budget_app",
        description="콘솔 가계부: 수입/지출 관리 프로그램",
    )
    parser.add_argument(
        "--data-dir", default="data", metavar="DIR",
        help="데이터 저장 디렉토리 (기본값: ./data)",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="DEBUG 레벨 로그 출력",
    )

    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    # add
    sub.add_parser("add", help="거래 추가 (대화형)")

    # list
    p = sub.add_parser("list", help="거래 목록 조회 (최신순)")
    p.add_argument("--limit", type=int, default=20, metavar="N",
                   help="최대 출력 건수 (기본: 20)")

    # search
    p = sub.add_parser("search", help="거래 검색 (최신순)")
    p.add_argument("--from", dest="from_date", metavar="DATE", help="시작 날짜 YYYY-MM-DD")
    p.add_argument("--to", dest="to_date", metavar="DATE", help="종료 날짜 YYYY-MM-DD")
    p.add_argument("--category", metavar="CAT", help="카테고리")
    p.add_argument("--type", metavar="TYPE", help="income | expense")
    p.add_argument("--q", metavar="KEYWORD", help="메모 키워드")
    p.add_argument("--tag", metavar="TAG", help="태그")

    # summary
    p = sub.add_parser("summary", help="월별 요약")
    p.add_argument("--month", required=True, metavar="YYYY-MM", help="대상 월")
    p.add_argument("--top", type=int, default=5, metavar="N", help="카테고리 TOP N (기본: 5)")

    # budget
    p_budget = sub.add_parser("budget", help="예산 관리")
    bs = p_budget.add_subparsers(dest="budget_action", metavar="action")
    bs.required = True
    p_bs = bs.add_parser("set", help="예산 설정")
    p_bs.add_argument("--month", required=True, metavar="YYYY-MM")
    p_bs.add_argument("--amount", required=True, type=int, metavar="N")
    p_bg = bs.add_parser("get", help="예산 조회")
    p_bg.add_argument("--month", required=True, metavar="YYYY-MM")

    # category
    p_cat = sub.add_parser("category", help="카테고리 관리")
    cs = p_cat.add_subparsers(dest="cat_action", metavar="action")
    cs.required = True
    cs.add_parser("list", help="목록 조회")
    cs.add_parser("add", help="카테고리 추가 (대화형)")
    cs.add_parser("remove", help="카테고리 삭제 (대화형)")

    # update
    p = sub.add_parser("update", help="거래 수정 (옵션 방식)")
    p.add_argument("--id", required=True, dest="tx_id", metavar="TX_ID")
    p.add_argument("--date", metavar="DATE")
    p.add_argument("--type", metavar="TYPE")
    p.add_argument("--category", metavar="CAT")
    p.add_argument("--amount", type=int, metavar="N")
    p.add_argument("--memo", metavar="TEXT")
    p.add_argument("--tags", metavar="TAG1,TAG2")

    # delete
    p = sub.add_parser("delete", help="거래 삭제")
    p.add_argument("--id", required=True, dest="tx_id", metavar="TX_ID")

    # import
    p = sub.add_parser("import", help="CSV 가져오기")
    p.add_argument("--from", required=True, dest="from_file", metavar="FILE")

    # export
    p = sub.add_parser("export", help="CSV 내보내기")
    p.add_argument("--out", required=True, metavar="FILE")
    p.add_argument("--month", metavar="YYYY-MM")
    p.add_argument("--from", dest="from_date", metavar="DATE")
    p.add_argument("--to", dest="to_date", metavar="DATE")

    # backup
    sub.add_parser("backup", help="데이터 백업 (타임스탬프 디렉토리)")

    return parser


_DISPATCH = {
    "add": cmd_add,
    "list": cmd_list,
    "search": cmd_search,
    "summary": cmd_summary,
    "budget": cmd_budget,
    "category": cmd_category,
    "update": cmd_update,
    "delete": cmd_delete,
    "import": cmd_import,
    "export": cmd_export,
    "backup": cmd_backup,
}


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    svc = LedgerService(Path(args.data_dir))
    handler = _DISPATCH[args.command]
    try:
        handler(svc, args)
        return 0
    except SystemExit as e:
        code = e.code
        if isinstance(code, int):
            return code
        return 1
