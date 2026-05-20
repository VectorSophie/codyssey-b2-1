from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Transaction:
    id: str
    type: str
    date: str
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "Transaction":
        tags = row.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        return cls(
            id=str(row["id"]),
            type=str(row["type"]),
            date=str(row["date"]),
            amount=int(row["amount"]),
            category=str(row["category"]),
            memo=str(row.get("memo", "")),
            tags=list(tags),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "date": self.date,
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "tags": self.tags,
        }


@dataclass(slots=True)
class Budget:
    month: str
    amount: int

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "Budget":
        return cls(month=str(row["month"]), amount=int(row["amount"]))

    def to_dict(self) -> dict[str, Any]:
        return {"month": self.month, "amount": self.amount}


@dataclass(slots=True)
class RecurringRule:
    id: str
    type: str
    day: int
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "RecurringRule":
        tags = row.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        return cls(
            id=str(row["id"]),
            type=str(row["type"]),
            day=int(row["day"]),
            amount=int(row["amount"]),
            category=str(row["category"]),
            memo=str(row.get("memo", "")),
            tags=list(tags),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "day": self.day,
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "tags": self.tags,
        }
