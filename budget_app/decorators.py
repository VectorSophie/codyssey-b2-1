from __future__ import annotations

import functools
import sys
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from .errors import AppError

P = ParamSpec("P")


def handle_cli_errors(func: Callable[P, int]) -> Callable[P, int]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        started = time.perf_counter()
        try:
            return func(*args, **kwargs)
        except AppError as exc:
            print(f"[오류] {exc.message}", file=sys.stderr)
            if exc.hint:
                print(f"[힌트] {exc.hint}", file=sys.stderr)
            return exc.exit_code
        except KeyboardInterrupt:
            print("[오류] 사용자가 작업을 취소했습니다.", file=sys.stderr)
            return 130
        except Exception:
            print("[오류] 알 수 없는 문제가 발생했습니다.", file=sys.stderr)
            print("[힌트] 입력값과 저장 파일 상태를 확인한 뒤 다시 실행하세요.", file=sys.stderr)
            return 1
        finally:
            elapsed = time.perf_counter() - started
            if elapsed > 5:
                print(f"[INFO] elapsed={elapsed:.2f}s", file=sys.stderr)

    return wrapper
