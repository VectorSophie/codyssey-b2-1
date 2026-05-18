from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Generator, Optional

from .models import Budget, Category, Transaction

_DEFAULT_CATEGORIES = [
    "food", "transport", "rent", "salary",
    "entertainment", "health", "other",
]


def _atomic_write(path: Path, lines: list[str]) -> None:
    """임시 파일에 쓴 뒤 rename으로 원자적 교체한다."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp", prefix=path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.writelines(lines)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class TransactionStore:
    def __init__(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self._path = data_dir / "transactions.jsonl"
        if not self._path.exists():
            self._path.touch()

    def stream(self) -> Generator[Transaction, None, None]:
        """파일을 한 줄씩 yield하는 제너레이터 (스트리밍)."""
        with self._path.open(encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if raw:
                    yield Transaction.from_dict(json.loads(raw))

    def append(self, tx: Transaction) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n")

    def _load_all(self) -> list[Transaction]:
        return list(self.stream())

    def _save_all(self, transactions: list[Transaction]) -> None:
        lines = [json.dumps(t.to_dict(), ensure_ascii=False) + "\n" for t in transactions]
        _atomic_write(self._path, lines)

    def next_id(self) -> str:
        max_num = 0
        for tx in self.stream():
            try:
                num = int(tx.id.removeprefix("TX-"))
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
        return f"TX-{max_num + 1:06d}"

    def get(self, tx_id: str) -> Optional[Transaction]:
        for tx in self.stream():
            if tx.id == tx_id:
                return tx
        return None

    def delete(self, tx_id: str) -> bool:
        all_tx = self._load_all()
        filtered = [t for t in all_tx if t.id != tx_id]
        if len(filtered) == len(all_tx):
            return False
        self._save_all(filtered)
        return True

    def update(self, tx_id: str, **fields: Any) -> bool:
        all_tx = self._load_all()
        for i, tx in enumerate(all_tx):
            if tx.id == tx_id:
                for k, v in fields.items():
                    setattr(all_tx[i], k, v)
                self._save_all(all_tx)
                return True
        return False


class CategoryStore:
    def __init__(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self._path = data_dir / "categories.jsonl"
        if not self._path.exists():
            self._path.touch()
            for name in _DEFAULT_CATEGORIES:
                self._append(name)

    def _append(self, name: str) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"name": name}, ensure_ascii=False) + "\n")

    def stream(self) -> Generator[Category, None, None]:
        with self._path.open(encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if raw:
                    yield Category.from_dict(json.loads(raw))

    def list_names(self) -> list[str]:
        return [c.name for c in self.stream()]

    def exists(self, name: str) -> bool:
        return name in self.list_names()

    def add(self, name: str) -> bool:
        if self.exists(name):
            return False
        self._append(name)
        return True

    def remove(self, name: str) -> bool:
        names = self.list_names()
        if name not in names:
            return False
        remaining = [n for n in names if n != name]
        lines = [json.dumps({"name": n}, ensure_ascii=False) + "\n" for n in remaining]
        _atomic_write(self._path, lines)
        return True


class BudgetStore:
    def __init__(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self._path = data_dir / "budgets.jsonl"
        if not self._path.exists():
            self._path.touch()

    def stream(self) -> Generator[Budget, None, None]:
        with self._path.open(encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if raw:
                    yield Budget.from_dict(json.loads(raw))

    def get(self, month: str) -> Optional[Budget]:
        for b in self.stream():
            if b.month == month:
                return b
        return None

    def set_budget(self, month: str, amount: int) -> None:
        budgets = [b for b in self.stream() if b.month != month]
        budgets.append(Budget(month=month, amount=amount))
        lines = [json.dumps(b.to_dict(), ensure_ascii=False) + "\n" for b in budgets]
        _atomic_write(self._path, lines)
