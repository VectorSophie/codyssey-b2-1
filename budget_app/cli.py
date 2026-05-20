from __future__ import annotations

import argparse
from pathlib import Path

from .decorators import handle_cli_errors
from .formatters import money, print_transactions
from .services import BudgetService, prompt_transaction
from .validators import validate_positive_int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m budget_app")
    parser.add_argument("--data-dir", default="./data", help="JSONL 저장 폴더 (기본: ./data)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("add", help="대화형 거래 추가")

    list_parser = sub.add_parser("list", help="최신순 거래 목록")
    list_parser.add_argument("--limit", type=int, default=20)

    search = sub.add_parser("search", help="조건 검색")
    search.add_argument("--from", dest="date_from")
    search.add_argument("--to", dest="date_to")
    search.add_argument("--category")
    search.add_argument("--type")
    search.add_argument("--q")
    search.add_argument("--tag")
    search.add_argument("--limit", type=int, default=100)

    summary = sub.add_parser("summary", help="월별 요약")
    summary.add_argument("--month", required=True)
    summary.add_argument("--top", type=int, default=3)

    budget = sub.add_parser("budget", help="예산 설정/조회")
    budget_sub = budget.add_subparsers(dest="budget_command", required=True)
    budget_set = budget_sub.add_parser("set", help="월 예산 저장")
    budget_set.add_argument("--month", required=True)
    budget_set.add_argument("--amount", required=True)

    category = sub.add_parser("category", help="카테고리 관리")
    category_sub = category.add_subparsers(dest="category_command", required=True)
    category_sub.add_parser("list", help="카테고리 목록")
    category_add = category_sub.add_parser("add", help="카테고리 추가")
    category_add.add_argument("name", nargs="?")
    category_remove = category_sub.add_parser("remove", help="카테고리 삭제")
    category_remove.add_argument("name")

    update = sub.add_parser("update", help="옵션 기반 거래 수정")
    update.add_argument("--id", required=True)
    update.add_argument("--date")
    update.add_argument("--type")
    update.add_argument("--category")
    update.add_argument("--amount")
    update.add_argument("--memo")
    update.add_argument("--tags")

    delete = sub.add_parser("delete", help="거래 삭제")
    delete.add_argument("--id", required=True)

    import_parser = sub.add_parser("import", help="CSV 가져오기")
    import_parser.add_argument("--from", dest="source", required=True)

    export = sub.add_parser("export", help="CSV 내보내기")
    export.add_argument("--out", required=True)
    export.add_argument("--month")
    export.add_argument("--from", dest="date_from")
    export.add_argument("--to", dest="date_to")

    sub.add_parser("backup", help="데이터 백업 생성")

    recurring = sub.add_parser("recurring", help="반복 내역")
    recurring_sub = recurring.add_subparsers(dest="recurring_command", required=True)
    recurring_add = recurring_sub.add_parser("add", help="반복 내역 등록")
    recurring_add.add_argument("--type", required=True)
    recurring_add.add_argument("--day", required=True)
    recurring_add.add_argument("--amount", required=True)
    recurring_add.add_argument("--category", required=True)
    recurring_add.add_argument("--memo", default="")
    recurring_add.add_argument("--tags", default="")
    recurring_apply = recurring_sub.add_parser("apply", help="특정 월 반복 내역 생성")
    recurring_apply.add_argument("--month", required=True)
    return parser


@handle_cli_errors
def run(args: argparse.Namespace) -> int:
    service = BudgetService(Path(args.data_dir))

    if args.command == "add":
        tx = prompt_transaction(service)
        print(f"[저장 완료] id={tx.id}")
        return 0

    if args.command == "list":
        print_transactions(service.list_transactions(validate_positive_int(args.limit, "limit")))
        return 0

    if args.command == "search":
        print_transactions(
            service.search_transactions(
                date_from=args.date_from,
                date_to=args.date_to,
                category=args.category,
                tx_type=args.type,
                query=args.q,
                tag=args.tag,
                limit=args.limit,
            )
        )
        return 0

    if args.command == "summary":
        top = validate_positive_int(args.top, "top")
        result = service.summary(args.month, top)
        if result["sample_count"] == 0:
            print("데이터 없음")
            return 0
        print(f"총 수입: {money(int(result['income']))}")
        print(f"총 지출: {money(int(result['expense']))}")
        print(f"잔액: {money(int(result['balance']))}")
        if result["budget"] is not None:
            print(f"예산: {money(int(result['budget']))} (사용률 {float(result['usage']):.1f}%)")
            if result["over_budget"]:
                print("[WARNING] 예산을 초과했습니다.")
        print("")
        print(f"지출 TOP {top}")
        for idx, (category, amount) in enumerate(result["top"], start=1):
            print(f"{idx}. {category} {money(amount)}")
        return 0

    if args.command == "budget":
        service.set_budget(args.month, args.amount)
        print(f"[저장 완료] {args.month} 예산 {money(int(args.amount))}")
        return 0

    if args.command == "category":
        if args.category_command == "list":
            for category in service.categories():
                print(f"- {category}")
            return 0
        if args.category_command == "add":
            name = args.name or input("카테고리명: ").strip()
            created = service.add_category(name)
            print(f"[저장 완료] category={name}" if created else f"[정보] 이미 존재합니다 category={name}")
            return 0
        removed = service.remove_category(args.name)
        print(f"[삭제 완료] category={args.name}" if removed else f"[정보] 없는 카테고리입니다 category={args.name}")
        return 0

    if args.command == "update":
        changed = service.update_transaction(
            args.id,
            {
                "date": args.date,
                "type": args.type,
                "category": args.category,
                "amount": args.amount,
                "memo": args.memo,
                "tags": args.tags,
            },
        )
        print(f"[수정 완료] id={args.id}" if changed else f"[정보] 없는 거래입니다 id={args.id}")
        return 0

    if args.command == "delete":
        changed = service.delete_transaction(args.id)
        print(f"[삭제 완료] id={args.id}" if changed else f"[정보] 없는 거래입니다 id={args.id}")
        return 0

    if args.command == "import":
        imported, skipped = service.import_csv(Path(args.source))
        print(f"[완료] imported={imported}, skipped={skipped}")
        return 0

    if args.command == "export":
        count = service.export_csv(Path(args.out), args.month, args.date_from, args.date_to)
        print(f"[완료] {args.out} ({count} records)")
        return 0

    if args.command == "backup":
        target = service.backup()
        print(f"[완료] backup={target}")
        return 0

    if args.command == "recurring":
        if args.recurring_command == "add":
            rule = service.add_recurring(args.type, args.day, args.amount, args.category, args.memo, args.tags)
            print(f"[저장 완료] recurring={rule.id}")
            return 0
        count = service.apply_recurring(args.month)
        print(f"[완료] created={count}")
        return 0

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)
