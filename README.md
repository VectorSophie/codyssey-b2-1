# 콘솔 가계부 (budget_app)

Python 표준 라이브러리만으로 구현한 파일 기반 가계부 CLI 프로그램.  
수입/지출 CRUD, 검색, 월별 요약, 예산 관리, CSV import/export를 지원한다.

## 1. 실행 환경

- Python 3.10 이상
- 외부 라이브러리 없음 (표준 라이브러리만 사용)

## 2. 실행 방법

```bash
# 프로젝트 루트에서 실행
python -m budget_app <command> [options]

# 전체 도움말
python -m budget_app --help

# 특정 명령 도움말
python -m budget_app list --help

# 데이터 디렉토리 지정 (기본값: ./data)
python -m budget_app --data-dir /path/to/data list

# DEBUG 로그 출력 (데코레이터 log_execution 추적)
python -m budget_app --debug list
```

초기 실행 시 `./data/` 디렉토리와 3개의 저장 파일이 자동 생성되며,
기본 카테고리 7개(food, transport, rent, salary, entertainment, health, other)가 등록된다.

## 3. 저장 파일 위치 및 형식

| 파일 | 형식 | 설명 |
|---|---|---|
| `data/transactions.jsonl` | JSONL | 거래 내역 (1건 = 1줄 JSON) |
| `data/categories.jsonl` | JSONL | 카테고리 목록 |
| `data/budgets.jsonl` | JSONL | 월별 예산 설정 |

### transactions.jsonl 예시

```jsonl
{"id": "TX-000001", "type": "expense", "date": "2024-01-15", "amount": 15000, "category": "food", "memo": "점심", "tags": ["meal"]}
{"id": "TX-000002", "type": "income", "date": "2024-01-14", "amount": 3000000, "category": "salary", "memo": "월급", "tags": []}
```

### categories.jsonl 예시

```jsonl
{"name": "food"}
{"name": "transport"}
```

### budgets.jsonl 예시

```jsonl
{"month": "2024-01", "amount": 500000}
```

## 4. 주요 명령 예시

### 거래 추가 (대화형)

```bash
$ python -m budget_app add
날짜(YYYY-MM-DD): 2024-01-15
타입(income/expense): expense
  카테고리: food, transport, rent, salary, entertainment, health, other
카테고리: food
금액(양수 정수): 15000
메모(선택, 없으면 엔터): 점심
태그(쉼표 구분, 없으면 엔터): meal
[저장 완료] id=TX-000001
```

### 거래 목록 조회

```bash
$ python -m budget_app list --limit 3
TX-000001 | 2024-01-15 | expense | food            |     15,000 | 점심                 [meal]
TX-000002 | 2024-01-14 | income  | salary          |  3,000,000 | 월급
TX-000003 | 2024-01-12 | expense | transport       |     20,000 | 버스
```

### 거래 검색

```bash
# 기간 + 타입 조합
$ python -m budget_app search --from 2024-01-01 --to 2024-01-31 --type expense

# 카테고리 + 키워드
$ python -m budget_app search --category food --q 점심

# 태그 검색
$ python -m budget_app search --tag meal
```

### 월별 요약

```bash
$ python -m budget_app summary --month 2024-01 --top 3
=== 2024-01 월별 요약 ===
총 수입:    3,000,000원
총 지출:      535,000원
잔액  :    2,465,000원
예산  :      600,000원 (사용률 89.2%)

지출 TOP 3
  1) rent               500,000원
  2) transport           20,000원
  3) food                15,000원
```

### 예산 설정 및 조회

```bash
$ python -m budget_app budget set --month 2024-01 --amount 600000
[저장 완료] 2024-01 예산 600,000원

$ python -m budget_app budget get --month 2024-01
2024-01 예산: 600,000원
```

### 카테고리 관리

```bash
$ python -m budget_app category list
  - food
  - transport
  ...

$ python -m budget_app category add
카테고리명: dining
[저장 완료] category=dining

$ python -m budget_app category remove
삭제할 카테고리명: dining
[삭제 완료] category=dining
```

### 거래 수정 (옵션 방식)

```bash
$ python -m budget_app update --id TX-000001 --amount 18000 --memo "점심 수정"
[수정 완료] id=TX-000001
```

### 거래 삭제

```bash
$ python -m budget_app delete --id TX-000001
[삭제 완료] id=TX-000001

# 없는 ID 처리
$ python -m budget_app delete --id TX-INVALID
[오류] id='TX-INVALID'를 찾을 수 없습니다.
```

### CSV 내보내기

```bash
# 월 기준
$ python -m budget_app export --out export.csv --month 2024-01
[완료] export.csv (12 records)

# 날짜 범위 기준
$ python -m budget_app export --out export.csv --from 2024-01-01 --to 2024-03-31
[완료] export.csv (35 records)
```

### CSV 가져오기

```bash
$ python -m budget_app import --from import.csv
[완료] imported=5, skipped=0
```

### 데이터 백업 (보너스)

```bash
$ python -m budget_app backup
[백업 완료] backup/20240115_143022
```

`backup/<타임스탬프>/` 디렉토리에 3개 JSONL 파일이 복사된다.

## 5. import/export CSV 스키마

| column | required | 형식 | 설명 |
|---|---|---|---|
| `date` | Y | YYYY-MM-DD | 거래 날짜 |
| `type` | Y | income / expense | 거래 유형 |
| `category` | Y | 문자열 | 카테고리명 (import 시 미등록 카테고리 자동 추가) |
| `amount` | Y | 양수 정수 | 금액 |
| `memo` | N | 문자열 | 메모 |
| `tags` | N | 쉼표(,) 구분 문자열 | 예: `meal,lunch` |

- 인코딩: UTF-8
- 헤더 행 포함 필수
- 잘못된 행(날짜 오류, 음수 금액 등)은 skipped 카운트에 포함되고 건너뜀

## 6. 프로젝트 구조

```
codyssey-b2-1/
├── budget_app/
│   ├── __init__.py       # 버전 정보
│   ├── __main__.py       # 진입점: python -m budget_app
│   ├── models.py         # 데이터 모델 (Transaction, Budget, Category)
│   ├── decorators.py     # 공통 데코레이터 (log_execution, timer, handle_errors)
│   ├── storage.py        # 파일 I/O 저장소 (TransactionStore, CategoryStore, BudgetStore)
│   ├── service.py        # 비즈니스 로직 (LedgerService)
│   └── cli.py            # CLI 파서 및 커맨드 핸들러
├── data/                 # 자동 생성 (첫 실행 시)
│   ├── transactions.jsonl
│   ├── categories.jsonl
│   └── budgets.jsonl
├── backup/               # backup 명령 실행 시 생성
└── README.md
```

## 7. 설계 포인트

### 제너레이터 스트리밍

`list`, `search`, `export`는 파일을 한 번에 메모리에 올리지 않고 `yield`로 한 줄씩 읽는다:

```python
def stream(self) -> Generator[Transaction, None, None]:
    with self._path.open(encoding="utf-8") as f:
        for raw in f:
            if raw.strip():
                yield Transaction.from_dict(json.loads(raw))
```

### 데코레이터 분리

`decorators.py`에 3종의 데코레이터를 구현해 공통 관심사를 분리한다:

| 데코레이터 | 역할 | 적용 위치 |
|---|---|---|
| `@log_execution` | 서비스 메서드 호출/완료를 DEBUG 레벨로 기록 | `service.py` 메서드 |
| `@timer` | 실행 시간이 0.1초 이상이면 경과 시간 출력 | `list`, `search`, `export` |
| `@handle_errors` | 예외를 스택트레이스 없이 원인+힌트로 출력 후 exit(1) | 모든 커맨드 핸들러 |

### 원자적 파일 쓰기

`update`, `delete` 시 임시 파일에 기록 후 `os.replace()`로 교체하여 데이터 손상을 방지한다:

```python
def _atomic_write(path, lines):
    fd, tmp = tempfile.mkstemp(dir=path.parent, ...)
    with os.fdopen(fd, "w") as f:
        f.writelines(lines)
    os.replace(tmp, path)   # 원자적 교체
```

### 타입 힌트

모든 함수와 메서드에 타입 힌트를 적용하여 계약을 명확히 한다:

```python
def export_csv(
    self,
    out_path: str,
    from_date: Optional[str] = None,
    month: Optional[str] = None,
) -> int: ...
```

## 8. 오류 처리

스택트레이스 없이 원인과 힌트를 출력하고 exit code 1로 종료:

```bash
$ python -m budget_app add
날짜(YYYY-MM-DD): 2024-13-40
[오류] 날짜 형식이 올바르지 않습니다.
[힌트] 예: 2024-01-15 (YYYY-MM-DD)

$ python -m budget_app delete --id TX-INVALID
[오류] id='TX-INVALID'를 찾을 수 없습니다.
```

- 정상 종료: exit code 0
- 오류 종료: exit code 1
- Ctrl+C: "중단" 메시지 후 exit code 0
