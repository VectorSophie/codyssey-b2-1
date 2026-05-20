from __future__ import annotations

from datetime import date, datetime

from .errors import AppError


VALID_TYPES = {"income", "expense"}


def validate_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise AppError("날짜 형식이 올바르지 않습니다.", "예: 2024-01-15") from exc
    return value


def validate_month(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise AppError("월 형식이 올바르지 않습니다.", "예: 2024-01") from exc
    return value


def validate_type(value: str) -> str:
    lowered = value.strip().lower()
    if lowered not in VALID_TYPES:
        raise AppError("거래 타입이 올바르지 않습니다.", "income 또는 expense 중 하나를 입력하세요.")
    return lowered


def validate_amount(value: str | int) -> int:
    try:
        amount = int(value)
    except (TypeError, ValueError) as exc:
        raise AppError("금액은 양수 정수여야 합니다.", "예: 15000") from exc
    if amount <= 0:
        raise AppError("금액은 0보다 커야 합니다.", "양수 정수를 입력하세요.")
    return amount


def validate_positive_int(value: str | int, name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise AppError(f"{name}은 양수 정수여야 합니다.", "1 이상의 정수를 입력하세요.") from exc
    if number <= 0:
        raise AppError(f"{name}은 0보다 커야 합니다.", "1 이상의 정수를 입력하세요.")
    return number


def validate_day(value: str | int) -> int:
    try:
        day = int(value)
    except (TypeError, ValueError) as exc:
        raise AppError("반복 일자는 1부터 31 사이 정수여야 합니다.", "예: 25") from exc
    if day < 1 or day > 31:
        raise AppError("반복 일자는 1부터 31 사이여야 합니다.", "월말은 해당 월의 마지막 날로 보정됩니다.")
    return day


def parse_tags(value: str | None) -> list[str]:
    if not value:
        return []
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def today_string() -> str:
    return date.today().strftime("%Y-%m-%d")
