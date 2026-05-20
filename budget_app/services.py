from __future__ import annotations

import calendar
import csv
import heapq
from dataclasses import replace
from pathlib import Path

from .errors import AppError
from .models import RecurringRule, Transaction
from .repository import JsonlStore, TransactionRepository
from .validators import (
    parse_tags,
    today_string,
    validate_amount,
    validate_date,
    validate_day,
    validate_month,
    validate_type,
)


class BudgetService:
    def __init__(self, data_dir: Path) -> None:
        self.store = JsonlStore(data_dir)
        self.transactions = TransactionRepository(self.store)
        self.store.ensure()

    def require_category(self, category: str) -> str:
        category = category.strip()
        if not category:
            raise AppError("카테고리가 비어 있습니다.", "category list로 사용 가능한 값을 확인하세요.")
        if category not in self.store.categories():
            raise AppError("등록되지 않은 카테고리입니다.", f"category add {category}로 먼저 등록하세요.")
        return category

    def add_transaction(
        self,
        tx_type: str,
        tx_date: str,
        amount: str | int,
        category: str,
        memo: str = "",
        tags: str | None = None,
    ) -> Transaction:
        tx = Transaction(
            id=self.store.next_transaction_id(),
            type=validate_type(tx_type),
            date=validate_date(tx_date),
            amount=validate_amount(amount),
            category=self.require_category(category),
            memo=memo,
            tags=parse_tags(tags),
        )
        self.transactions.add(tx)
        return tx

    def list_transactions(self, limit: int) -> list[Transaction]:
        return heapq.nlargest(limit, self.transactions.iter_all(), key=lambda tx: (tx.date, tx.id))

    def search_transactions(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        category: str | None = None,
        tx_type: str | None = None,
        query: str | None = None,
        tag: str | None = None,
        limit: int = 100,
    ) -> list[Transaction]:
        if date_from:
            validate_date(date_from)
        if date_to:
            validate_date(date_to)
        if tx_type:
            tx_type = validate_type(tx_type)
        if category:
            self.require_category(category)
        query_lower = query.lower() if query else None

        def matches(tx: Transaction) -> bool:
            if date_from and tx.date < date_from:
                return False
            if date_to and tx.date > date_to:
                return False
            if category and tx.category != category:
                return False
            if tx_type and tx.type != tx_type:
                return False
            if query_lower and query_lower not in tx.memo.lower():
                return False
            if tag and tag not in tx.tags:
                return False
            return True

        return heapq.nlargest(
            limit,
            (tx for tx in self.transactions.iter_all() if matches(tx)),
            key=lambda tx: (tx.date, tx.id),
        )

    def set_budget(self, month: str, amount: str | int) -> None:
        self.store.set_budget(validate_month(month), validate_amount(amount))

    def summary(self, month: str, top: int) -> dict[str, object]:
        month = validate_month(month)
        income = 0
        expense = 0
        by_category: dict[str, int] = {}
        sample_count = 0
        for tx in self.transactions.iter_all():
            if not tx.date.startswith(month):
                continue
            sample_count += 1
            if tx.type == "income":
                income += tx.amount
            else:
                expense += tx.amount
                by_category[tx.category] = by_category.get(tx.category, 0) + tx.amount
        ranked = sorted(by_category.items(), key=lambda item: item[1], reverse=True)[:top]
        budget = self.store.get_budget(month)
        usage = (expense / budget.amount * 100) if budget else None
        return {
            "month": month,
            "income": income,
            "expense": expense,
            "balance": income - expense,
            "top": ranked,
            "budget": budget.amount if budget else None,
            "usage": usage,
            "over_budget": bool(budget and expense > budget.amount),
            "sample_count": sample_count,
        }

    def categories(self) -> list[str]:
        return self.store.categories()

    def add_category(self, name: str) -> bool:
        name = name.strip()
        if not name:
            raise AppError("카테고리명이 비어 있습니다.", "비어 있지 않은 이름을 입력하세요.")
        return self.store.add_category(name)

    def remove_category(self, name: str) -> bool:
        name = name.strip()
        transactions = list(self.transactions.iter_all())
        if any(tx.category == name for tx in transactions):
            raise AppError("사용 중인 카테고리는 삭제할 수 없습니다.", "거래를 다른 카테고리로 수정한 뒤 삭제하세요.")
        return self.store.remove_category(name)

    def update_transaction(self, tx_id: str, changes: dict[str, object]) -> bool:
        if not changes:
            raise AppError("수정할 값이 없습니다.", "예: update --id TX-000001 --amount 20000")

        def updater(tx: Transaction) -> Transaction:
            values = {}
            if "date" in changes and changes["date"] is not None:
                values["date"] = validate_date(str(changes["date"]))
            if "type" in changes and changes["type"] is not None:
                values["type"] = validate_type(str(changes["type"]))
            if "category" in changes and changes["category"] is not None:
                values["category"] = self.require_category(str(changes["category"]))
            if "amount" in changes and changes["amount"] is not None:
                values["amount"] = validate_amount(changes["amount"])
            if "memo" in changes and changes["memo"] is not None:
                values["memo"] = str(changes["memo"])
            if "tags" in changes and changes["tags"] is not None:
                values["tags"] = parse_tags(str(changes["tags"]))
            return replace(tx, **values)

        return self.transactions.update(tx_id, updater)

    def delete_transaction(self, tx_id: str) -> bool:
        return self.transactions.delete(tx_id)

    def import_csv(self, source: Path) -> tuple[int, int]:
        imported = 0
        skipped = 0
        with source.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"date", "type", "category", "amount"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise AppError("CSV 헤더가 올바르지 않습니다.", "date,type,category,amount,memo,tags 헤더가 필요합니다.")
            for row in reader:
                try:
                    self.add_transaction(
                        tx_type=row.get("type", ""),
                        tx_date=row.get("date", ""),
                        amount=row.get("amount", ""),
                        category=row.get("category", ""),
                        memo=row.get("memo", "") or "",
                        tags=row.get("tags", "") or "",
                    )
                    imported += 1
                except AppError:
                    skipped += 1
        return imported, skipped

    def export_csv(
        self,
        target: Path,
        month: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> int:
        if month:
            validate_month(month)
        elif not (date_from and date_to):
            raise AppError("export 조건이 필요합니다.", "--month 또는 --from/--to를 지정하세요.")
        if date_from:
            validate_date(date_from)
        if date_to:
            validate_date(date_to)

        def include(tx: Transaction) -> bool:
            if month:
                return tx.date.startswith(month)
            return bool(date_from and date_to and date_from <= tx.date <= date_to)

        rows = [tx for tx in self.transactions.iter_all() if include(tx)]
        rows.sort(key=lambda tx: (tx.date, tx.id), reverse=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["date", "type", "category", "amount", "memo", "tags"])
            writer.writeheader()
            for tx in rows:
                writer.writerow(
                    {
                        "date": tx.date,
                        "type": tx.type,
                        "category": tx.category,
                        "amount": tx.amount,
                        "memo": tx.memo,
                        "tags": ",".join(tx.tags),
                    }
                )
        return len(rows)

    def backup(self) -> Path:
        return self.store.backup()

    def add_recurring(
        self,
        tx_type: str,
        day: str | int,
        amount: str | int,
        category: str,
        memo: str = "",
        tags: str | None = None,
    ) -> RecurringRule:
        rule = RecurringRule(
            id=self.store.next_recurring_id(),
            type=validate_type(tx_type),
            day=validate_day(day),
            amount=validate_amount(amount),
            category=self.require_category(category),
            memo=memo,
            tags=parse_tags(tags),
        )
        self.store.add_recurring(rule)
        return rule

    def apply_recurring(self, month: str) -> int:
        month = validate_month(month)
        _, last_day = calendar.monthrange(int(month[:4]), int(month[5:7]))
        created = 0
        existing_keys = {
            (tx.date, tx.type, tx.category, tx.amount, tx.memo, tuple(tx.tags))
            for tx in self.transactions.iter_all()
            if tx.date.startswith(month)
        }
        for rule in self.store.iter_recurring():
            day = min(rule.day, last_day)
            tx_date = f"{month}-{day:02d}"
            key = (tx_date, rule.type, rule.category, rule.amount, rule.memo, tuple(rule.tags))
            if key in existing_keys:
                continue
            self.add_transaction(
                tx_type=rule.type,
                tx_date=tx_date,
                amount=rule.amount,
                category=rule.category,
                memo=rule.memo,
                tags=",".join(rule.tags),
            )
            created += 1
        return created


def prompt_transaction(service: BudgetService) -> Transaction:
    tx_date = input(f"날짜(YYYY-MM-DD, 기본 {today_string()}): ").strip() or today_string()
    tx_type = input("타입(income/expense): ").strip()
    print("카테고리:", ", ".join(service.categories()))
    category = input("카테고리: ").strip()
    amount = input("금액(양수): ").strip()
    memo = input("메모(선택): ").strip()
    tags = input("태그(쉼표로 구분, 없으면 엔터): ").strip()
    return service.add_transaction(tx_type, tx_date, amount, category, memo, tags)
