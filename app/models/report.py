"""ERD와 1:1 대응하는 10개 물리 테이블의 SQLAlchemy ORM 선언.
10개 테이블(분류·공통 보고서·벡터·상세 6종·Prompt 버전)을 Python 클래스로 매핑하고,
카테고리 코드 -> 상세 모델·상세 필드 대응표(DETAIL_MODELS, DETAIL_FIELDS)를 제공
"""
from datetime import datetime, date
from sqlalchemy import (BigInteger, Integer, String, Text, Date, DateTime, ForeignKey,
                        Identity, CheckConstraint, UniqueConstraint, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import VECTOR

# ============================================================
# ORM 기반 클래스
# ============================================================
# 모든 테이블 클래스가 상속한다.
class Base(DeclarativeBase):
    pass

# ============================================================
# 분류 테이블: report_categories (6행)
# ============================================================
# - category_id : PK (1~6)
# - code        : EXPERIMENT 등 6종 코드 (UNIQUE)
# - name        : 이름 (예: 실험 결과 보고서)
# - description : 설명 (NULL 허용)
class ReportCategory(Base):
    __tablename__='report_categories'
    category_id: Mapped[int] = mapped_column(Integer,primary_key=True)
    code: Mapped[str] = mapped_column(Text,unique=True,nullable=False)
    name: Mapped[str] = mapped_column(Text,nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

# ============================================================
# 공통 보고서 테이블: reports
# ============================================================
# - report_id    : PK, DB가 자동 부여 (Identity)
# - category_id  : 분류 FK. ondelete='RESTRICT' -> 보고서가 있는 분류는 삭제 불가
# - overview     : 검색용 개요 (최대 1000자). E5 벡터의 원문
# - index_status : 벡터 색인 상태 (기본 pending, 색인 후 ready)
# - revision     : 수정 횟수 기반 버전 (생성 1, PUT마다 +1)
class Report(Base):
    __tablename__='reports'
    report_id: Mapped[int] = mapped_column(BigInteger, Identity(),primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey('report_categories.category_id',ondelete='RESTRICT'),nullable=False)
    overview: Mapped[str] = mapped_column(String(1000),nullable=False)
    index_status: Mapped[str] = mapped_column(String(20),default='pending',nullable=False)
    revision: Mapped[int] = mapped_column(Integer,default=1,nullable=False)

# ============================================================
# 개요 벡터 테이블: report_embeddings (보고서당 1행)
# ============================================================
# - report_id        : PK 겸 FK. ondelete='CASCADE' -> 보고서 삭제 시 벡터도 삭제
# - embedding        : pgvector VECTOR(384)
# - model_name       : 모델 이름
# - overview_hash    : 개요 원문 SHA-256 (64자)
# - indexed_revision : 벡터를 만들 때의 reports.revision
# - indexed_at       : 색인 시각 (기본값 DB now())
class ReportEmbedding(Base):
    __tablename__='report_embeddings'
    report_id: Mapped[int] = mapped_column(ForeignKey('reports.report_id',ondelete='CASCADE'),primary_key=True)
    embedding: Mapped[list[float]] = mapped_column(VECTOR(384),nullable=False)
    model_name: Mapped[str] = mapped_column(Text,nullable=False)
    overview_hash: Mapped[str] = mapped_column(String(64),nullable=False)
    indexed_revision: Mapped[int] = mapped_column(Integer,nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)

# ============================================================
# 상세 테이블 공통 컬럼 Mixin
# ============================================================
# 공통 필드를 종류별로 실제 보유한다는 요구사항에 맞춰 6개 상세 엔터티에 같은 Mixin 사용.
# - title / content / author : 보고서 제목(200자)·본문·작성자(100자)
# - create_at / update_at    : 생성·수정 시각 (timezone 포함)
class DetailMixin:
    title: Mapped[str] = mapped_column(String(200),nullable=False)
    content: Mapped[str] = mapped_column(Text,nullable=False)
    author: Mapped[str] = mapped_column(String(100),nullable=False)
    create_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    update_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)

# ============================================================
# 이하는 Mixin 컬럼을 공유하는 상세 테이블 6종
# ============================================================
# 모든 상세 테이블의 report_id는 reports PK를 가리키는 PK 겸 FK이며 해당 reports가 삭제될 경우 삭제된다(CASCADE).

# --------------------------------------------------------
# 실험 결과 보고서: experiment_reports
# --------------------------------------------------------
class ExperimentReport(DetailMixin,Base):
    __tablename__='experiment_reports'
    report_id: Mapped[int] = mapped_column(ForeignKey('reports.report_id',ondelete='CASCADE'),primary_key=True)
    experiment_date: Mapped[date] = mapped_column(Date,nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text,nullable=False)
    result_summary: Mapped[str] = mapped_column(Text,nullable=False)

# --------------------------------------------------------
# 일일 업무 보고서: daily_work_reports
# --------------------------------------------------------
class DailyWorkReport(DetailMixin,Base):
    __tablename__='daily_work_reports'
    report_id: Mapped[int] = mapped_column(ForeignKey('reports.report_id',ondelete='CASCADE'),primary_key=True)
    work_date: Mapped[date] = mapped_column(Date,nullable=False)
    progress: Mapped[str] = mapped_column(Text,nullable=False)
    blockers: Mapped[str] = mapped_column(Text,default='',nullable=False)   # 빈 문자열 허용

# --------------------------------------------------------
# 연구 계획서: research_plans
# --------------------------------------------------------
class ResearchPlan(DetailMixin,Base):
    __tablename__='research_plans'
    report_id: Mapped[int] = mapped_column(ForeignKey('reports.report_id',ondelete='CASCADE'),primary_key=True)
    research_goal: Mapped[str] = mapped_column(Text,nullable=False)
    methodology: Mapped[str] = mapped_column(Text,nullable=False)
    target_date: Mapped[date] = mapped_column(Date,nullable=False)

# --------------------------------------------------------
# 데이터 처리 보고서: data_processing_reports
# --------------------------------------------------------
class DataProcessingReport(DetailMixin,Base):
    __tablename__='data_processing_reports'
    report_id: Mapped[int] = mapped_column(ForeignKey('reports.report_id',ondelete='CASCADE'),primary_key=True)
    dataset_name: Mapped[str] = mapped_column(Text,nullable=False)
    processing_steps: Mapped[str] = mapped_column(Text,nullable=False)
    quality_notes: Mapped[str] = mapped_column(Text,default='',nullable=False)  # 빈 문자열 허용

# --------------------------------------------------------
# 프롬프트 보고서: prompt_reports
# --------------------------------------------------------
class PromptReport(DetailMixin,Base):
    __tablename__='prompt_reports'
    report_id: Mapped[int] = mapped_column(ForeignKey('reports.report_id',ondelete='CASCADE'),primary_key=True)
    purpose: Mapped[str] = mapped_column(Text,nullable=False)
    # active_version_no : 현재 활성 프롬프트 버전 번호 (생성 시 1)
    active_version_no: Mapped[int] = mapped_column(Integer,default=1,nullable=False)

# --------------------------------------------------------
# 회의록: meeting_minutes
# --------------------------------------------------------
class MeetingMinute(DetailMixin,Base):
    __tablename__='meeting_minutes'
    report_id: Mapped[int] = mapped_column(ForeignKey('reports.report_id',ondelete='CASCADE'),primary_key=True)
    meeting_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)    # timezone 포함
    attendees: Mapped[str] = mapped_column(Text,nullable=False)
    decisions: Mapped[str] = mapped_column(Text,nullable=False)

# ============================================================
# Prompt 버전 테이블: prompt_versions
# ============================================================
# - prompt_version_id : PK, 자동 부여
# - report_id         : prompt_reports FK (CASCADE 삭제)
# - version_no        : 보고서 안의 버전 번호. (report_id, version_no) UNIQUE
# - prompt_text       : 해당 버전의 프롬프트 본문
# - created_at        : 생성 시각
class PromptVersion(Base):
    __tablename__='prompt_versions'
    __table_args__=(UniqueConstraint('report_id','version_no',name='uq_prompt_versions_report_no'),)
    prompt_version_id: Mapped[int] = mapped_column(BigInteger,Identity(),primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey('prompt_reports.report_id',ondelete='CASCADE'),nullable=False)
    version_no: Mapped[int] = mapped_column(Integer,nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text,nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)

# ============================================================
# 카테고리 코드 대응표
# ============================================================
# 추가 테이블은 만들지 않는다. 보고서 종류마다 Detail Class만 매핑한다.
# DETAIL_MODELS : 6종의 카테고리 코드 -> 상세 ORM 클래스 매핑
DETAIL_MODELS={
 'EXPERIMENT':ExperimentReport,'DAILY_WORK':DailyWorkReport,
 'RESEARCH_PLAN':ResearchPlan,'DATA_PROCESSING':DataProcessingReport,
 'PROMPT':PromptReport,'MEETING':MeetingMinute,
}
# DETAIL_FIELDS : 카테고리 코드 -> API 응답 details에 넣을 상세 컬럼 순서
DETAIL_FIELDS={
 'EXPERIMENT':('experiment_date','hypothesis','result_summary'),
 'DAILY_WORK':('work_date','progress','blockers'),
 'RESEARCH_PLAN':('research_goal','methodology','target_date'),
 'DATA_PROCESSING':('dataset_name','processing_steps','quality_notes'),
 'PROMPT':('purpose','active_version_no'),
 'MEETING':('meeting_at','attendees','decisions'),
}
