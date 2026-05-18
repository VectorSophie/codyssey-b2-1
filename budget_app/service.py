from __future__ import annotations
import csv
import shutil
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from .decorators import log_execution
from .models import Budget, Transaction
from .storage import BudgetStore, CategoryStore, TransactionStore


class LedgerService:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.tx_store = TransactionStore(data_dir)
        self.cat_store = CategoryStore(data_dir)
        self.budget_store = BudgetStore(data_dir)

    # ── Transactions ────────────────────────────────────────────────────────

    @log_execution
    def add_transaction(
        self,
        type_: str,
        date_: str,
        amount: int,
        category: str,
        memo: str = "",
        tags: Optional[list[str]] = None,
    ) -> Transaction:
        tx = Transaction(
            id=self.tx_store.next_id(),
            type=type_,
            date=date_,
            amount=amount,
            category=category,
            memo=memo,
            tags=tags or [],
        )
        self.tx_store.append(tx)
        return tx

    @log_execution
    def stream_all(self) -> Generator[Transaction, None, None]:
        return self.tx_store.stream()

    @log_execution
    def search(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: Optional[str] = None,
        type_: Optional[str] = None,
        q: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Generator[Transaction, None, None]:
        for tx in self.tx_store.stream():
            if from_date and tx.date < from_date:
                continue
            if to_date and tx.date > to_date:
                continue
            if category and tx.category != category:
                continue
            if type_ and tx.type != type_:
                continue
            if q and q.lower() not in tx.memo.lower():
                continue
            if tag and tag not in tx.tags:
                continue
            yield tx

    @log_execution
    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        return self.tx_store.get(tx_id)

    @log_execution
    def update_transaction(self, tx_id: str, **fields) -> bool:
        return self.tx_store.update(tx_id, **fields)

    @log_execution
    def delete_transaction(self, tx_id: str) -> bool:
        return self.tx_store.delete(tx_id)

    # ── Summary ─────────────────────────────────────────────────────────────

    def monthly_summary(self, month: str, top_n: int = 5) -> dict:
        prefix = month + "-"
        income = 0
        expense = 0
        cat_totals: dict[str, int] = {}

        for tx in self.tx_store.stream():
            if not tx.date.startswith(prefix):
                continue
            if tx.type == "income":
                income += tx.amount
            else:
                expense += tx.amount
                cat_totals[tx.category] = cat_totals.get(tx.category, 0) + tx.amount

        top_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
        budget = self.budget_store.get(month)

        return {
            "month": month,
            "income": income,
            "expense": expense,
            "balance": income - expense,
            "top_categories": top_cats,
            "budget": budget,
            "has_data": income > 0 or expense > 0,
        }

    # ── Budget ───────────────────────────────────────────────────────────────

    def set_budget(self, month: str, amount: int) -> None:
        self.budget_store.set_budget(month, amount)

    def get_budget(self, month: str) -> Optional[Budget]:
        return self.budget_store.get(month)

    # ── Categories ───────────────────────────────────────────────────────────

    def list_categories(self) -> list[str]:
        return self.cat_store.list_names()

    def category_exists(self, name: str) -> bool:
        return self.cat_store.exists(name)

    def add_category(self, name: str) -> bool:
        return self.cat_store.add(name)

    def remove_category(self, name: str) -> tuple[bool, str]:
        for tx in self.tx_store.stream():
            if tx.category == name:
                return False, f"'{name}'을(를) 사용하는 내역이 있습니다. 먼저 해당 내역을 수정하거나 삭제하세요."
        if not self.cat_store.remove(name):
            return False, f"'{name}'은(는) 존재하지 않는 카테고리입니다."
        return True, ""

    # ── Import / Export ──────────────────────────────────────────────────────

    CSV_FIELDS = ["date", "type", "category", "amount", "memo", "tags"]

    def export_csv(
        self,
        out_path: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        month: Optional[str] = None,
    ) -> int:
        if month:
            from_date = f"{month}-01"
            to_date = f"{month}-31"

        count = 0
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
            writer.writeheader()
            for tx in self.tx_store.stream():
                if from_date and tx.date < from_date:
                    continue
                if to_date and tx.date > to_date:
                    continue
                writer.writerow({
                    "date": tx.date,
                    "type": tx.type,
                    "category": tx.category,
                    "amount": tx.amount,
                    "memo": tx.memo,
                    "tags": ",".join(tx.tags),
                })
                count += 1
        return count

    def import_csv(self, in_path: str) -> tuple[int, int]:
        imported = 0
        skipped = 0
        with open(in_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    date_ = row["date"].strip()
                    datetime.strptime(date_, "%Y-%m-%d")
                    type_ = row["type"].strip()
                    if type_ not in ("income", "expense"):
                        raise ValueError("type must be income or expense")
                    amount = int(row["amount"])
                    if amount <= 0:
                        raise ValueError("amount must be positive")
                    category = row["category"].strip()
                    if not self.cat_store.exists(category):
                        self.cat_store.add(category)
                    tags_raw = row.get("tags", "").strip()
                    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
                    self.add_transaction(
                        type_=type_,
                        date_=date_,
                        amount=amount,
                        category=category,
                        memo=row.get("memo", "").strip(),
                        tags=tags,
                    )
                    imported += 1
                except (KeyError, ValueError):
                    skipped += 1
        return imported, skipped

    # ── Backup ──────────────────────────────────────────────────────────────

    def backup(self, backup_dir: Optional[Path] = None) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = (backup_dir or self.data_dir.parent / "backup") / ts
        dest.mkdir(parents=True, exist_ok=True)
        for f in self.data_dir.glob("*.jsonl"):
            shutil.copy2(f, dest / f.name)
        return dest
