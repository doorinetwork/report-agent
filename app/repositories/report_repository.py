"""Repository: 영속 저장·조회만 담당. 외부 API/Embedding 요청은 여기서 하지 않습니다."""
from datetime import date,datetime,timezone
from typing import Any
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from app.models.report import (ReportCategory,Report,ReportEmbedding,DETAIL_MODELS,DETAIL_FIELDS,
                               PromptVersion)
from app.services.errors import DomainError

# ============================================================
# [요구사항 B-05] 카테고리 코드 -> 분류 행 조회 (category_for_code)
# ============================================================
# code에 해당하는 ReportCategory 1건을 반환한다
# - 등록된 코드 (예: 'EXPERIMENT') : ReportCategory(category_id=1, ...) 반환
# - 등록되지 않은 코드             : 422 VALIDATION_ERROR
def category_for_code(db: Session, code: str) -> ReportCategory:
    category = db.scalar(select(ReportCategory).where(ReportCategory.code == code))
    if category is None: raise DomainError(422, 'VALIDATION_ERROR','등록되지 않은 카테고리입니다.')
    return category

# ============================================================
# [요구사항 B-06] 공통 보고서 + 분류 + 상세 행 조회 (get_report_and_detail)
# ============================================================
# 보고서 ID 하나로 (Report, ReportCategory, 상세 행) 세 객체를 함께 반환한다
# - lock=False      : 일반 조회
# - lock=True       : SELECT ... FOR UPDATE 로 행 잠금 (수정 Transaction 안에서 사용)
# - 없는 ID          : 404 REPORT_NOT_FOUND
# - 상세 행이 없음    : 500 DATA_INTEGRITY_ERROR (공통 행만 있고 상세가 누락된 손상 데이터)
def get_report_and_detail(db: Session, rid: int, lock: bool = False):
    # -- 공통 보고서 행 조회 (필요 시 잠금) --
    stmt = select(Report).where(Report.report_id == rid)
    if lock:stmt = stmt.with_for_update()
    report = db.scalar(stmt)
    if report is None: raise DomainError(404, 'REPORT_NOT_FOUND', '요청한 보고서를 찾을 수 없습니다.')
    # -- 분류 -> 카테고리에 맞는 상세 모델로 상세 행 조회 --
    category = db.get(ReportCategory, report.category_id)
    detail = db.get(DETAIL_MODELS[category.code], rid)
    if detail is None: raise DomainError(500, 'DATA_INTEGRITY_ERROR', '보고서 상세 행이 누락되었습니다.')
    return report, category, detail

# ============================================================
# [요구사항 B-06] JSON 직렬화용 값 변환 (plain_value)
# ============================================================
# DB에서 읽은 값을 JSON에 넣을 수 있는 값으로 바꾼다
# - 시간대 있는 datetime : UTC ISO 8601 + 'Z' (예: 2026-11-19 18:00+09:00 -> '2026-11-19T09:00:00Z')
# - 시간대 없는 datetime : 500 DATA_INTEGRITY_ERROR
# - date                : 'YYYY-MM-DD' (예: date(2026,11,19) -> '2026-11-19')
# - 그 밖의 값           : 그대로 반환
def plain_value(obj:Any):
    if isinstance(obj,datetime):
        if obj.tzinfo is None or obj.utcoffset() is None:
            raise DomainError(500,'DATA_INTEGRITY_ERROR','시각 데이터에 시간대가 없습니다.')
        return obj.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
    if isinstance(obj,date):return obj.isoformat()
    return obj

# ============================================================
# [요구사항 B-06] [API-03] 단일 응답 형식으로 묶기 (serialize_report)
# ============================================================
# Report·ReportCategory·상세 행을 API-03 JSON dict 하나로 만든다
# - title/content/author/created_at/updated_at : 상세 테이블에서 가져옴
# - overview/revision/index_status             : 공통 reports 테이블에서 가져옴
# - details                                    : DETAIL_FIELDS 순서의 카테고리별 속성
def serialize_report(report: Report, category: ReportCategory, detail) -> dict:
    # -- 카테고리별 details 구성 --
    keys = [k for k in DETAIL_FIELDS[category.code] if k != 'active_version_no']
    values = {k:plain_value(getattr(detail,k)) for k in keys}
    if category.code == 'PROMPT': values['active_version_no'] = detail.active_version_no
    # -- API-03 응답 dict --
    # - report_id     : 보고서 ID
    # - category_code : 분류 코드
    # - title / content / author : 상세 테이블 값
    # - overview      : 검색용 개요
    # - details       : 위에서 만든 카테고리별 속성
    # - revision      : 현재 버전
    # - index_status  : 벡터 색인 상태 (ready/pending)
    # - created_at / updated_at : UTC 'Z' 문자열
    return {
        'report_id': report.report_id, 
        'category_code': category.code,
        'title': detail.title,
        'content': detail.content,
        'author': detail.author,
        'overview': report.overview,
        'details': values,
        'revision': report.revision, 
        'index_status': report.index_status,
        # DB column spelling create_at/update_at. API contract uses created_at/updated_at.
        'created_at': plain_value(detail.create_at), 
        'updated_at': plain_value(detail.update_at)
    }

# ============================================================
# [요구사항 B-06] 단일 보고서 조회 (read_report)
# ============================================================
def read_report(db: Session, rid: int) -> dict:
    return serialize_report(*get_report_and_detail(db, rid))

# ============================================================
# [요구사항 B-07] 제목 부분 검색·목록 조회 (list_reports)
# ============================================================
# report_read_view에서 목록·전체 건수를 조회한다
# - title=None            : 전체 목록
# - title='가중치'        : 제목에 '가중치'가 들어간 보고서 (대소문자 구분 없음)
# - 결과 0건              : {'items': [], 'total': 0, ...} (HTTP 200)
# 정렬: update_at DESC, report_id DESC (최근 수정 순, 같으면 큰 ID 먼저)
def list_reports(db:Session, title:str|None,limit:int,offset:int,
                 category_code:str|None=None,updated_after:datetime|None=None)->dict:
    # UNION ALL VIEW: 원문은 자식 테이블이 단일 진실 공급원입니다.
    conditions=[];params={'limit':limit,'offset':offset}
    if title:
        # LIKE 특수문자를 escape하지 않으면 사용자 '%'가 와일드카드가 됩니다.
        escaped=title.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        conditions.append("title ILIKE :pat ESCAPE '\\'")
        params['pat']='%'+escaped+'%'
    if category_code:
        conditions.append('category_code=:category_code');params['category_code']=category_code
    if updated_after:
        conditions.append('update_at>=:updated_after');params['updated_after']=updated_after
    where=(' WHERE '+' AND '.join(conditions)) if conditions else ''
    total=db.execute(text('SELECT count(*) FROM report_read_view'+where),params).scalar_one()
    rows=db.execute(text('SELECT report_id,category_code,title,revision FROM report_read_view'+where+
                         ' ORDER BY update_at DESC,report_id DESC LIMIT :limit OFFSET :offset'),params).mappings().all()
    return {'items':[dict(r) for r in rows],'total':total,'limit':limit,'offset':offset}
