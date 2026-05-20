# 파일 기반 가계부 CLI

Python 표준 라이브러리만 사용하는 콘솔 가계부입니다. 실행 방식은 `python -m budget_app <command> [options]`이며 데이터는 JSONL 파일로 영구 저장합니다.

## 실행 방법

```sh
cd <제출 폴더>
python3 -m budget_app --help
```

기본 저장 폴더는 현재 작업 디렉터리의 `./data`입니다. 다른 위치를 쓰려면 모든 명령 앞에 `--data-dir <경로>`를 붙입니다.

```sh
python3 -m budget_app --data-dir ./my-data category list
```

## 저장 파일

저장 형식은 JSONL로 고정했습니다. 파일이 없으면 자동 생성되고, 카테고리 파일이 비어 있으면 기본 카테고리 `food`, `transport`, `rent`, `salary`, `utilities`, `health`, `education`, `entertainment`, `etc`가 자동 생성됩니다.

| 파일 | 역할 |
|---|---|
| `data/transactions.jsonl` | 거래 내역 |
| `data/categories.jsonl` | 카테고리 |
| `data/budgets.jsonl` | 월 예산 |
| `data/recurring.jsonl` | 보너스 반복 내역 |

## 주요 명령

```sh
python3 -m budget_app add
```

```sh
python3 -m budget_app list --limit 10
```

```sh
python3 -m budget_app search --from 2024-01-01 --to 2024-01-31 --category food --type expense --q 점심 --tag meal
```

```sh
python3 -m budget_app budget set --month 2024-01 --amount 500000
python3 -m budget_app summary --month 2024-01 --top 3
```

```sh
python3 -m budget_app category add hobby
python3 -m budget_app category list
python3 -m budget_app category remove hobby
```

`update`는 옵션 방식으로 고정했습니다.

```sh
python3 -m budget_app update --id TX-000001 --amount 20000 --memo "저녁" --tags meal,dinner
python3 -m budget_app delete --id TX-000001
```

## CSV 가져오기/내보내기

CSV는 UTF-8, 헤더 포함 형식입니다.

| column | required | 설명 |
|---|---|---|
| `date` | Y | `YYYY-MM-DD` |
| `type` | Y | `income` 또는 `expense` |
| `category` | Y | 등록된 카테고리 |
| `amount` | Y | 양수 정수 |
| `memo` | N | 문자열 |
| `tags` | N | 쉼표로 구분한 문자열 |

```sh
python3 -m budget_app import --from import.csv
python3 -m budget_app export --out export.csv --month 2024-01
python3 -m budget_app export --out export.csv --from 2024-01-01 --to 2024-01-31
```

## 보너스 명령

```sh
python3 -m budget_app backup
```

```sh
python3 -m budget_app recurring add --type income --day 25 --amount 3000000 --category salary --memo "월급"
python3 -m budget_app recurring apply --month 2024-02
```

## 오류 처리

잘못된 날짜, 0 이하 금액, 허용되지 않은 거래 타입, 없는 카테고리는 스택트레이스 대신 `[오류]`와 `[힌트]`를 출력합니다. 정상 종료는 exit code `0`, 오류 종료는 0이 아닌 exit code를 사용합니다.

## 구현 메모

- `Transaction`, `Budget`, `RecurringRule`, 저장소와 서비스 클래스로 책임을 분리했습니다.
- 거래 목록과 검색은 JSONL 파일을 제너레이터로 읽고 필요한 최신 결과만 보관합니다.
- `update`와 `delete`는 임시 파일을 작성한 뒤 `os.replace`로 교체합니다.
- 공통 CLI 오류 처리는 데코레이터로 분리했습니다.
