"""보고서 Router: Path/Query/JSON/HTTP Status와 Service 호출만 담당합니다."""

from datetime import datetime
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.report import CategoryCode
from app.services import report_service
from app.core.config import at_least
from app.services.errors import DomainError

# ============================================================
# Router 생성
# ============================================================
router=APIRouter(prefix='/api/v1',tags=['Reports & Categories'])

# ============================================================
# [요구사항 B-04] [API-01] 카테고리 조회 (categories)
# ============================================================
# GET /api/v1/categories -> 200 {"items": [...6개...]}
# db=Depends(get_db) : FastAPI가 요청마다 Session을 만들어 전달
@router.get('/categories')
def categories(db:Session=Depends(get_db)):
    return report_service.categories(db)

# ============================================================
# [요구사항 B-07] [API-04] 제목 부분 검색·목록 조회 (list_reports)
# ============================================================
# GET /api/v1/reports?title=가중치&limit=20&offset=0
# Query 인자:
# - title=None                      : 제목 부분 검색어 (없으면 전체)
# - limit=Query(20, ge=1, le=100)   : 페이지 크기 1~100, 기본 20
# - offset=Query(0, ge=0)           : 건너뛸 개수 0 이상, 기본 0
@router.get('/reports')
def list_reports(title:str|None=None,limit:int=Query(20,ge=1,le=100),
                 offset:int=Query(0,ge=0),category_code:CategoryCode|None=None,
                 updated_after:datetime|None=None,db:Session=Depends(get_db)):
    if not at_least('intermediate') and (category_code is not None or updated_after is not None):
        raise DomainError(422,'VALIDATION_ERROR','추가 필터는 Intermediate 기능입니다.')
    return report_service.list_reports(db,title,limit,offset,category_code,updated_after)

# ============================================================
# [요구사항 B-06] [API-03] ID로 보고서 조회 (get_report)
# ============================================================
# GET /api/v1/reports/12 -> 200 단일 보고서 / 없는 ID일 경우 -> 404 REPORT_NOT_FOUND
@router.get('/reports/{report_id}')
def get_report(report_id:int=Path(ge=1),db:Session=Depends(get_db)):
    return report_service.get_report(db,report_id)
