from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Transaction:
    id: str
    type: str       # "income" | "expense"
    date: str       # YYYY-MM-DD
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "date": self.date,
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Transaction:
        return cls(
            id=d["id"],
            type=d["type"],
            date=d["date"],
            amount=int(d["amount"]),
            category=d["category"],
            memo=d.get("memo", ""),
            tags=d.get("tags") or [],
        )


@dataclass
class Budget:
    month: str   # YYYY-MM
    amount: int

    def to_dict(self) -> dict:
        return {"month": self.month, "amount": self.amount}

    @classmethod
    def from_dict(cls, d: dict) -> Budget:
        return cls(month=d["month"], amount=int(d["amount"]))


@dataclass
class Category:
    name: str

    def to_dict(self) -> dict:
        return {"name": self.name}

    @classmethod
    def from_dict(cls, d: dict) -> Category:
        return cls(name=d["name"])
