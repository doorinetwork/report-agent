"""환경 설정. 실제 비밀번호와 API 키는 .env에만 두고 Git에 올리지 않습니다."""
from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

# ============================================================
# 1. .env 파일 위치 결정과 환경변수 적재
# ============================================================
# parents[2] : config.py -> core -> app -> 프로젝트 루트
ROOT = Path(__file__).resolve().parents[2]
# override=False : 터미널에서 이미 설정한 환경변수가 있으면 .env 값보다 우선
load_dotenv(ROOT / '.env', override=False)

# ============================================================
# 2. 설정 객체 정의
# ============================================================
# frozen=True : 실행 중 설정값을 바꿀 수 없는 불변 객체로 만든다
@dataclass(frozen=True)
class Settings:
    # 운영 원칙: 설정은 프로젝트 밖에 공유하지 않고 로그에도 출력하지 않습니다.
    # - database_url          : PostgreSQL 접속 문자열 (예: postgresql+psycopg://postgres:...@localhost:5432/report_agent_lab)
    # - embedding_model       : E5 모델 (384차원)
    # - search_min_similarity : 의미 검색 채택 최소 Cosine 유사도 (기본 0.75)
    # - llm_model             : LLM 모델 이름 (.env에서 지정)
    # - llm_timeout           : LLM 호출 제한 시간(초)
    # - llm_max_tokens        : LLM 최대 출력 토큰 수
    # - project_level         : basic / intermediate / advanced
    database_url: str = os.getenv('DATABASE_URL', '')
    embedding_model: str = os.getenv('EMBEDDING_MODEL', 'intfloat/multilingual-e5-small')
    search_min_similarity: float = float(os.getenv('SEARCH_MIN_SIMILARITY','0.75'))
    llm_model: str = os.getenv('LLM_MODEL','')
    llm_timeout: float = float(os.getenv('LLM_TIMEOUT_SECONDS','30'))
    llm_max_tokens: int = int(os.getenv('LLM_MAX_OUTPUT_TOKENS','400'))
    project_level: str = os.getenv('PROJECT_LEVEL', 'basic').lower()

settings = Settings()

# ============================================================
# 3. 난이도 비교 함수
# ============================================================
def at_least(level: str) -> bool:
    order = {'basic':1,'intermediate':2,'advanced':3}
    return order.get(settings.project_level,1)>=order[level]
