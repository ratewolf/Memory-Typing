# 데이터 형식

## 권장 입력 형식: JSON 버전 1

TXT는 문단과 문장 경계를 추론해야 하고, 분리된 문장 앞에 공백이 붙을 수 있다. 기본 가져오기
형식은 경계를 직접 표현하는 UTF-8 JSON으로 한다. UI의 `JSON 가져오기`와 기본 샘플도 이 형식을
사용한다. 기존 `TxtImporter`는 이전 파일과 코드의 호환을 위해 남겨 두지만 새 콘텐츠에는 JSON을
권장한다.

최상위 `format_version`은 정수 `1`이어야 한다. 모든 `id`는 파일 전체에서 유일하고 비어 있지
않아야 하며, 한번 정한 ID는 편집하거나 다시 가져올 때도 유지한다. 배열의 위치가 각 엔터티의
`source_order`가 된다.

```json
{
  "format_version": 1,
  "book": {
    "id": "book-memory",
    "title": "기억 연습",
    "chapters": [
      {
        "id": "chapter-1",
        "title": "첫 장",
        "paragraphs": [
          {
            "id": "paragraph-1",
            "sentences": [
              { "id": "sentence-1", "text": "첫 문장입니다." },
              { "id": "sentence-2", "text": "두 번째 문장입니다." }
            ]
          }
        ]
      }
    ]
  }
}
```

## 텍스트 정규화 규칙

- `sentences` 배열의 각 항목이 문장 하나다. 마침표나 물음표 등 문장 부호로 경계를 추론하지
  않는다.
- `text`는 정본 `Sentence.original_text`가 된다. 비어 있는 문장과 문장 앞뒤의 공백·탭·줄바꿈은
  오류로 거부한다.
- 한 문단의 문장은 ASCII 공백 한 칸으로 연결해 `Paragraph.original_text`를 만든다.
- 내용이 있는 문단과 장은 `\n\n`으로 연결해 각각 `Chapter.original_text`와
  `Book.original_text`를 만든다. 빈 배열은 원문에 불필요한 구분자를 추가하지 않는다.
- 문장 내부의 연속 공백, 문장부호, 한국어와 영어 혼합 텍스트는 그대로 보존한다.
- 빈 `chapters`, `paragraphs`, `sentences` 배열은 허용한다. 따라서 아직 내용이 없는 구조도
  명시적으로 표현할 수 있다.

이 규칙 때문에 문장 데이터 자체에 우연한 선행 공백이 들어가지 않고, 같은 JSON을 다시
가져오면 항상 같은 계층·순서·원문·ID를 얻는다. 실제 예시는
`sample_data/korean_sample.json`에서 확인할 수 있다.

## 콘텐츠 계층

```text
Book
└── Chapter
    └── Paragraph
        └── Sentence
```

가져오기 결과의 도메인 객체는 목록 위치와 무관한 문자열 ID와 0부터 시작하는 `source_order`를
가진다. 자식 목록은 JSON 순서대로 정렬된 불변 튜플이다. 이벤트용 `display_text`나 사용자의
`typed_text`는 `original_text`를 덮어쓰지 않는다.

## 기존 TXT 가져오기

`TxtImporter`는 기존 호출자를 위해 유지한다. TXT 파일 하나를 책과 장 하나로 만들고, 빈 줄로
문단을 나누며, 종결 문장부호 뒤의 공백 경계로 문장을 추정한다. 파일 전체 원문은 보존하지만
분리된 뒤쪽 문장에 선행 공백이 포함될 수 있고 문장부호가 없는 경계를 알 수 없으므로 UI의 기본
가져오기 방식에서는 제외한다.

## 로컬 저장 범위

가져온 계층은 현재 SQLite의 books, chapters, paragraphs, sentences 테이블에 저장할 수 있다.
향후 사용자 작성 퀴즈, 학습 세션, 문장 시도, 이벤트 시도, 퀴즈 시도 및 복습 통계를 저장할 수
있어야 한다. 스키마 버전과 마이그레이션은 명시적으로 관리하며, 가져오기나 원문 편집 때문에
기존 학습 이력을 자동 삭제하지 않는다.
