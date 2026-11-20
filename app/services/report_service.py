"""Report Service: 6종 보고서 공통 CRUD/버전/동기화. Repository는 DB, Service는 업무 규칙."""

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.report import ReportCategory
from app.repositories import report_repository as repo

# ============================================================
# [요구사항 B-04] [API-01] 카테고리 목록 (categories)
# ============================================================
# report_categories를 category_id 오름차순으로 읽어 items 목록으로 반환한다
def categories(db:Session)->dict:
    rows=db.scalars(select(ReportCategory).order_by(ReportCategory.category_id)).all()
    return {'items':[{'category_id':r.category_id,'code':r.code,'name':r.name,'description':r.description} for r in rows]}

# ============================================================
# [요구사항 B-06] [API-03] 단일 조회 (get_report)
# ============================================================
# Repository의 read_report()를 그대로 호출.
def get_report(db:Session,rid:int)->dict:
    return repo.read_report(db,rid)

# ============================================================
# [요구사항 B-07] [API-04] 목록 조회 (list_reports)
# ============================================================
# Repository의 레포트 리스트를 조회
def list_reports(db:Session,title:str|None,limit:int,offset:int,
                 category_code:str|None=None,updated_after:datetime|None=None):
    return repo.list_reports(db,title,limit,offset,category_code,updated_after)
