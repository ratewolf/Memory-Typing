# Memory Typing

책의 내용을 직접 입력하며 암기하는 개인용 오프라인 데스크톱 애플리케이션입니다.
한국어 입력을 중심으로 책과 장을 선택하고, 문장 단위로 원문을 따라 입력하며 정확도와
진행 상태를 바로 확인할 수 있습니다.

## 현재 기능

- UTF-8 JSON 파일에서 `Book → Chapter → Paragraph → Sentence` 콘텐츠 가져오기
- 가져온 책과 장 선택 및 문장 순서에 따른 타이핑 학습
- 문자별 정답·오답 표시, 정확도, 진행률 및 문장 자동 이동
- 마지막 한글 조합까지 원문과 일치하면 구분자 없이 확정하는 Qt IME 상태 처리
- 원문과 학습자 입력을 분리한 순수 Python 타이핑 엔진
- 가져온 책, 학습 세션 및 완료한 문장 시도를 보존하는 SQLite 저장소
- 확장 가능한 학습 이벤트 생명주기와 결정론적 테스트를 위한 난수 주입

로컬 데이터베이스는 운영체제의 애플리케이션 데이터 디렉터리에 생성됩니다. 가져온 책은
재시작 후에도 서재에 표시되며, 문장 입력을 시작하면 장 단위 학습 세션을 만들고 완료한 문장의
최종 타이핑 상태와 시간·속도 지표를 기록합니다. 실제 빈칸·회상 이벤트, 사용자 작성 퀴즈,
학습 이력 조회 화면, 결과 화면 및 복습 기능은 후속 개발 범위입니다.

JSON 입력 규격과 예시는 [`docs/DATA_FORMAT.md`](docs/DATA_FORMAT.md) 및
[`sample_data/korean_sample.json`](sample_data/korean_sample.json)에서 확인할 수 있습니다.

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

실제 한국어 IME 조합 동작은 헤드리스 자동 테스트만으로 검증할 수 없습니다. 관련 변경 후에는
[`docs/MANUAL_QA.md`](docs/MANUAL_QA.md)의 수동 점검도 수행해야 합니다.

## Docker

Docker 이미지는 테스트와 헤드리스 실행 환경을 재현하기 위한 용도입니다.

```bash
docker build -t memory-typing .
docker run --rm memory-typing pytest
```

기본 컨테이너 실행은 Qt의 `offscreen` 플랫폼을 사용하므로 실제 창을 표시하지 않습니다.
GUI는 로컬 데스크톱 환경에서 실행해 확인하세요.

