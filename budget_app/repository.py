from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Callable, Iterable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from .errors import AppError
from .models import Budget, RecurringRule, Transaction


DEFAULT_CATEGORIES = [
    "food",
    "transport",
    "rent",
    "salary",
    "utilities",
    "health",
    "education",
    "entertainment",
    "etc",
]

T = TypeVar("T")


class JsonlStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.transactions_path = data_dir / "transactions.jsonl"
        self.categories_path = data_dir / "categories.jsonl"
        self.budgets_path = data_dir / "budgets.jsonl"
        self.recurring_path = data_dir / "recurring.jsonl"

    def ensure(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for path in [
            self.transactions_path,
            self.categories_path,
            self.budgets_path,
            self.recurring_path,
        ]:
            path.touch(exist_ok=True)
        if self.categories_path.stat().st_size == 0:
            self.write_categories(DEFAULT_CATEGORIES)

    def _read_jsonl_rows(self, path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
        self.ensure()
        with path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise AppError(
                        f"저장 파일을 읽을 수 없습니다: {path.name}:{line_no}",
                        "파일 형식이 JSONL인지 확인하세요.",
                    ) from exc
                if not isinstance(data, dict):
                    raise AppError(
                        f"저장 파일 행이 올바르지 않습니다: {path.name}:{line_no}",
                        "각 줄은 JSON 객체여야 합니다.",
                    )
                yield line_no, data

    def _read_jsonl(self, path: Path) -> Iterator[dict[str, Any]]:
        for _, row in self._read_jsonl_rows(path):
            yield row

    def _read_models(self, path: Path, factory: Callable[[dict[str, Any]], T], label: str) -> Iterator[T]:
        for line_no, row in self._read_jsonl_rows(path):
            try:
                yield factory(row)
            except (KeyError, TypeError, ValueError) as exc:
                raise AppError(
                    f"저장 파일 행이 올바르지 않습니다: {path.name}:{line_no}",
                    f"{label} 필드와 값 형식을 확인하세요.",
                ) from exc

    def _append_jsonl(self, path: Path, row: dict[str, Any]) -> None:
        self.ensure()
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    def _rewrite_jsonl(self, path: Path, rows: Iterable[dict[str, Any]]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=self.data_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def iter_transactions(self) -> Iterator[Transaction]:
        yield from self._read_models(self.transactions_path, Transaction.from_dict, "거래")

    def add_transaction(self, tx: Transaction) -> None:
        self._append_jsonl(self.transactions_path, tx.to_dict())

    def rewrite_transactions(self, rows: Iterable[Transaction]) -> None:
        self._rewrite_jsonl(self.transactions_path, (tx.to_dict() for tx in rows))

    def get_transaction(self, tx_id: str) -> Transaction | None:
        transactions = list(self.iter_transactions())
        for tx in transactions:
            if tx.id == tx_id:
                return tx
        return None

    def next_transaction_id(self) -> str:
        max_number = 0
        for tx in self.iter_transactions():
            if tx.id.startswith("TX-"):
                try:
                    max_number = max(max_number, int(tx.id.split("-", 1)[1]))
                except ValueError:
                    continue
        return f"TX-{max_number + 1:06d}"

    def categories(self) -> list[str]:
        names = []
        for row in self._read_jsonl(self.categories_path):
            name = str(row.get("name", "")).strip()
            if name:
                names.append(name)
        if not names:
            self.write_categories(DEFAULT_CATEGORIES)
            names = DEFAULT_CATEGORIES.copy()
        return sorted(set(names))

    def write_categories(self, categories: Iterable[str]) -> None:
        rows = ({"name": category} for category in sorted(set(categories)))
        self._rewrite_jsonl(self.categories_path, rows)

    def add_category(self, name: str) -> bool:
        categories = set(self.categories())
        if name in categories:
            return False
        categories.add(name)
        self.write_categories(categories)
        return True

    def remove_category(self, name: str) -> bool:
        categories = set(self.categories())
        if name not in categories:
            return False
        categories.remove(name)
        self.write_categories(categories)
        return True

    def iter_budgets(self) -> Iterator[Budget]:
        yield from self._read_models(self.budgets_path, Budget.from_dict, "예산")

    def set_budget(self, month: str, amount: int) -> None:
        seen = False
        budgets = []
        for budget in self.iter_budgets():
            if budget.month == month:
                budgets.append(Budget(month=month, amount=amount))
                seen = True
            else:
                budgets.append(budget)
        if not seen:
            budgets.append(Budget(month=month, amount=amount))
        self._rewrite_jsonl(self.budgets_path, (budget.to_dict() for budget in budgets))

    def get_budget(self, month: str) -> Budget | None:
        budgets = list(self.iter_budgets())
        for budget in budgets:
            if budget.month == month:
                return budget
        return None

    def iter_recurring(self) -> Iterator[RecurringRule]:
        yield from self._read_models(self.recurring_path, RecurringRule.from_dict, "반복 내역")

    def next_recurring_id(self) -> str:
        max_number = 0
        for rule in self.iter_recurring():
            if rule.id.startswith("RR-"):
                try:
                    max_number = max(max_number, int(rule.id.split("-", 1)[1]))
                except ValueError:
                    continue
        return f"RR-{max_number + 1:06d}"

    def add_recurring(self, rule: RecurringRule) -> None:
        self._append_jsonl(self.recurring_path, rule.to_dict())

    def validate_all(self) -> None:
        list(self.iter_transactions())
        self.categories()
        list(self.iter_budgets())
        list(self.iter_recurring())

    def backup(self) -> Path:
        self.ensure()
        self.validate_all()
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        target = self.data_dir / "backups" / f"budget_backup_{stamp}"
        target.mkdir(parents=True, exist_ok=False)
        for path in [
            self.transactions_path,
            self.categories_path,
            self.budgets_path,
            self.recurring_path,
        ]:
            shutil.copy2(path, target / path.name)
        return target


class TransactionRepository:
    def __init__(self, store: JsonlStore) -> None:
        self.store = store

    def add(self, tx: Transaction) -> None:
        self.store.add_transaction(tx)

    def iter_all(self) -> Iterator[Transaction]:
        yield from self.store.iter_transactions()

    def update(self, tx_id: str, updater: Callable[[Transaction], Transaction]) -> bool:
        changed = False

        def rows() -> Iterator[Transaction]:
            nonlocal changed
            for tx in self.store.iter_transactions():
                if tx.id == tx_id:
                    changed = True
                    yield updater(tx)
                else:
                    yield tx

        buffered = list(rows())
        if changed:
            self.store.rewrite_transactions(buffered)
        return changed

    def delete(self, tx_id: str) -> bool:
        changed = False

        def rows() -> Iterator[Transaction]:
            nonlocal changed
            for tx in self.store.iter_transactions():
                if tx.id == tx_id:
                    changed = True
                    continue
                yield tx

        buffered = list(rows())
        if changed:
            self.store.rewrite_transactions(buffered)
        return changed
