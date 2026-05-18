from __future__ import annotations
import functools
import logging
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger("budget_app")

F = TypeVar("F", bound=Callable[..., Any])


def log_execution(fn: F) -> F:
    """서비스 메서드 호출/완료를 DEBUG 레벨로 기록한다."""
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger.debug("[call] %s", fn.__qualname__)
        result = fn(*args, **kwargs)
        logger.debug("[done] %s", fn.__qualname__)
        return result
    return wrapper  # type: ignore[return-value]


def timer(fn: F) -> F:
    """실행 시간이 0.1초 이상이면 경과 시간을 출력한다."""
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        if elapsed >= 0.1:
            print(f"  ({elapsed:.3f}s)")
        return result
    return wrapper  # type: ignore[return-value]


def handle_errors(fn: F) -> F:
    """예외를 스택트레이스 없이 원인 + 힌트로 출력하고 exit(1)한다."""
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n[중단] 사용자가 입력을 취소했습니다.")
            raise SystemExit(0)
        except SystemExit:
            raise
        except Exception as exc:
            print(f"[오류] {exc}")
            raise SystemExit(1)
    return wrapper  # type: ignore[return-value]
