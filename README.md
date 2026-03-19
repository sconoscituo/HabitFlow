# HabitFlow
> 습관 추적 + AI 코칭 + 주간 리포트 서비스

## 개요

HabitFlow는 사용자의 습관 형성을 돕는 AI 코칭 서비스입니다.
매일 습관 수행 여부를 기록하고, Gemini AI가 스트릭 데이터를 분석해 맞춤 코칭 메시지를 제공합니다.
매주 월요일 오전 8시에 프리미엄 사용자에게 주간 리포트를 자동 생성합니다.

**수익 구조**: 무료 플랜(습관 3개) / 프리미엄 플랜(무제한 + AI 코칭 + 주간 리포트)

## 기술 스택

- **Backend**: FastAPI 0.104, Python 3.11
- **DB**: SQLAlchemy 2.0 (async) + SQLite (aiosqlite)
- **AI**: Google Gemini API (습관 코칭, 주간 리포트 생성)
- **스케줄러**: APScheduler 3.10 (매주 월요일 08:00 KST)
- **인증**: JWT (python-jose) + bcrypt
- **배포**: Docker + docker-compose

## 시작하기

### 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 다음 값을 설정합니다:

| 변수명 | 설명 |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API 키 |
| `DATABASE_URL` | SQLite DB 경로 (기본값 사용 가능) |
| `SECRET_KEY` | JWT 서명용 시크릿 키 |
| `DEBUG` | 개발 환경 여부 (True/False) |

### 실행 방법

#### Docker (권장)

```bash
docker-compose up -d
```

#### 직접 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

서버 실행 후 http://localhost:8000/docs 에서 API 문서를 확인하세요.

## API 문서

| 메서드 | 엔드포인트 | 설명 |
|---|---|---|
| GET | `/` | 헬스체크 |
| GET | `/health` | 상세 헬스체크 (스케줄러 상태 포함) |
| POST | `/api/v1/users/register` | 회원가입 |
| POST | `/api/v1/users/login` | 로그인 (JWT 발급) |
| GET | `/api/v1/users/me` | 내 정보 조회 |
| POST | `/api/v1/habits/` | 습관 생성 |
| GET | `/api/v1/habits/` | 내 습관 목록 조회 |
| POST | `/api/v1/habits/{id}/log` | 습관 수행 기록 |
| GET | `/api/v1/habits/{id}/streak` | 스트릭 조회 |
| GET | `/api/v1/reports/` | 주간 리포트 목록 |
| GET | `/api/v1/reports/latest` | 최신 리포트 조회 |

## 수익 구조

- **무료 플랜**: 습관 3개 추적, 기본 스트릭 통계
- **프리미엄 플랜** (월 5,900원): 습관 무제한, AI 맞춤 코칭 메시지, 주간 AI 리포트, 습관 달성 배지
- **연간 구독** (59,000원): 프리미엄 2개월 무료 혜택

## 라이선스

MIT
