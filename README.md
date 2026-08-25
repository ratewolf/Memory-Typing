# Memory Typing

책의 내용을 직접 입력하며 암기하는 개인용 오프라인 데스크톱 애플리케이션입니다.
현재 저장소에는 초기 프로젝트 구조와 최소 실행 창만 포함되어 있습니다.

## 요구 사항

- Python 3.12 이상
- 데스크톱 환경(PySide6 창 표시용)

## 로컬 설치

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## 실행

```bash
memory-typing
```

또는 다음과 같이 모듈로 실행할 수 있습니다.

```bash
python -m memory_typing.main
```

## 검사

```bash
pytest
ruff check .
ruff format --check .
```

## Docker

Docker 이미지는 테스트와 헤드리스 실행 환경을 재현하기 위한 용도입니다.

```bash
docker build -t memory-typing .
docker run --rm memory-typing pytest
```

기본 컨테이너 실행은 Qt의 `offscreen` 플랫폼을 사용하므로 실제 창을 표시하지 않습니다.
GUI는 로컬 데스크톱 환경에서 실행해 확인하세요.

