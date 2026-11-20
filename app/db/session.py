"""SQLAlchemy DB 연결과 세션 수명 관리. HTTP 요청당 세션을 하나 사용합니다."""
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.errors import DomainError

# ============================================================
# 1. DB Engine 생성 (프로세스당 1개)
# ============================================================
@lru_cache(maxsize=1)
def get_engine():
    if not settings.database_url or 'CHANGE_ME' in settings.database_url:
        raise DomainError(503,'DB_UNAVAILABLE','DATABASE_URL에 PostgreSQL 접속 정보를 설정하세요 (.env).')
    # pool_pre_ping=True : 풀에서 꺼낸 연결이 끊겼는지 먼저 확인
    # pool_size=5        : 기본으로 유지하는 연결 수
    # max_overflow=5     : 바쁠 때 추가로 허용하는 연결 수
    return create_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)

# ============================================================
# 2. Session Factory 생성 (프로세스당 1개)
# ============================================================
@lru_cache(maxsize=1)
def get_session_factory():
    # expire_on_commit=False : commit 후에도 ORM 객체 속성을 다시 조회하지 않고 읽을 수 있음
    # autoflush=False        : 조회 전에 자동 flush하지 않음 (flush 시점을 서비스가 명시적으로 결정)
    return sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)

# ============================================================
# 3. 요청 단위 Session 제공 (FastAPI 의존성)
# ============================================================
def get_db():
    # Router에서 Depends(get_db)로 사용. 서비스에서 commit 또는 rollback합니다.
    with get_session_factory()() as db:
        yield db
