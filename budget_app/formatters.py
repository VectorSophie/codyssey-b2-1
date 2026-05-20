from __future__ import annotations

import unicodedata

from .models import Transaction


TABLE_COLUMNS = [
    ("ID", 9, "left"),
    ("DATE", 10, "left"),
    ("TYPE", 7, "left"),
    ("CATEGORY", 14, "left"),
    ("AMOUNT", 10, "right"),
    ("MEMO", 20, "left"),
    ("TAGS", 0, "left"),
]


def money(value: int) -> str:
    return f"{value:,}원"


def display_width(value: str) -> int:
    width = 0
    for char in value:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
    return width


def pad_display(value: object, width: int, align: str = "left") -> str:
    text = str(value)
    if width <= 0:
        return text
    padding = max(width - display_width(text), 0)
    if align == "right":
        return " " * padding + text
    return text + " " * padding


def format_row(values: list[object]) -> str:
    cells = [
        pad_display(value, width, align)
        for value, (_, width, align) in zip(values, TABLE_COLUMNS)
    ]
    return " | ".join(cells).rstrip()


def format_transaction(tx: Transaction) -> str:
    tags = ",".join(tx.tags)
    return format_row([tx.id, tx.date, tx.type, tx.category, tx.amount, tx.memo, tags])


def print_transactions(rows: list[Transaction]) -> None:
    if not rows:
        print("데이터 없음")
        return
    print(format_row([label for label, _, _ in TABLE_COLUMNS]))
    print("-" * display_width(format_row([label for label, _, _ in TABLE_COLUMNS])))
    for tx in rows:
        print(format_transaction(tx))
