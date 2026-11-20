"""Postman JSON 계약을 Pydantic v2 모델로 표현합니다."""
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

# ============================================================
# 카테고리 코드 타입
# ============================================================
# 6종 이외의 문자열은 Pydantic이 422로 거절
CategoryCode=Literal['EXPERIMENT','DAILY_WORK','RESEARCH_PLAN','DATA_PROCESSING','PROMPT','MEETING']

# ============================================================
# [API-02] 보고서 등록 요청
# ============================================================
# - category_code : 6종 중 하나
# - title         : 1~200자
# - author        : 1~100자
# - content       : 1~20000자
# - overview      : 10~1000자
# - details       : 카테고리별 상세 속성 dict
class ReportCreate(BaseModel):
    category_code: CategoryCode
    title: str = Field(min_length = 1, max_length = 200)
    author: str = Field(min_length = 1, max_length = 100)
    content: str = Field(min_length = 1, max_length = 20000)
    overview: str = Field(min_length = 10, max_length = 1000)
    details: dict[str, Any]

    @field_validator('title','author','content','overview')
    @classmethod
    # 공백을 제외한 길이 검사
    # - overview             : 공백 제외 10자 미만이면 오류
    # - title/author/content : 공백만 있으면 오류
    def nonempty(cls, v, info):
        # DB CHECK가 trim한 문자열 길이를 검사하므로 API에서도 사전 검증합니다.
        min_len = 10 if info.field_name == 'overview' else 1
        if len(v.strip()) < min_len:
            raise ValueError(f'{info.field_name}: 공백 제외 최소 {min_len}자 필요')
        return v

# ============================================================
# [API-05] 보고서 전체 수정 요청
# ============================================================
class ReportUpdate(BaseModel):
    # category_code를 포함한 명세 밖 필드는 조용히 버리지 않고 422로 거절합니다.
    model_config={'extra':'forbid'}
    title: str = Field(min_length = 1, max_length = 200)
    author: str = Field(min_length = 1, max_length = 100)
    content: str = Field(min_length = 1, max_length = 20000)
    overview: str = Field(min_length = 10, max_length = 1000)
    details: dict[str, Any]
    expected_revision: int | None = Field(default = None, ge = 1)

    @field_validator('title','author','content','overview')
    @classmethod
    # 공백 제외 길이 검사
    def nonempty(cls, v, info):
        min_len = 10 if info.field_name == 'overview' else 1
        if len(v.strip()) < min_len:
            raise ValueError(f'{info.field_name}: 공백 제외 최소 {min_len}자 필요')
        return v

# ============================================================
# [API-07] 유사도 검색 요청
# ============================================================
# - query          : 1~200자
# - category_code  : 선택 (null이면 전체)
# - keyword_limit  : Keyword 후보 수 1~100 (기본 20)
# - semantic_limit : Semantic 후보 수 1~100 (기본 20)
class SimilarRequest(BaseModel):
    query: str = Field(min_length = 1, max_length = 200)
    category_code: CategoryCode | None = None
    keyword_limit: int = Field(default = 20, ge = 1, le = 100)
    semantic_limit: int = Field(default = 20, ge = 1, le = 100)

    # mode='before' : 길이 검사 전에 공백을 먼저 제거 (예: '  가중치 ' -> '가중치', ' ' -> 오류)
    @field_validator('query', mode = 'before')
    @classmethod
    def nonempty_query(cls, v):
        # 명세의 1~200자는 앞뒤 공백을 제거한 검색어 길이입니다.
        if isinstance(v, str):
            v = v.strip()
            if not v:raise ValueError('검색어를 입력하세요.')
        return v

# ============================================================
# [API-08] LLM 보고서 요약 요청
# ============================================================
# - max_sentences : 최대 문장 수 1~10 (기본 3)
class SummaryRequest(BaseModel):
    style: Literal['brief', 'structured'] = 'brief'
    max_sentences: int = Field(default = 3, ge = 1, le = 10)

# ============================================================
# [API-09] Agent 실행 요청
# ============================================================
# - action     : get_report / find_report / summarize_report / search_and_summarize
# - report_id  : report ID
# - query      : 최대 200자
# - agent_mode : 'tool_calling'
# - message    : Tool Calling 자연어 요청 (최대 1000자)
class AgentRequest(BaseModel):
    action: Literal['get_report', 'find_report', 'summarize_report', 'search_and_summarize'] | None = None
    report_id: int | None = Field(default = None, ge = 1)
    query: str | None = Field(default=None, max_length = 200)
    agent_mode: Literal['tool_calling'] | None = None
    message: str | None = Field(default = None, max_length = 1000)

    @field_validator('query', mode = 'before')
    @classmethod
    def normalize_query(cls, v):
        return v.strip() if isinstance(v, str) else v

# ============================================================
# Prompt 버전 관련 요청
# ============================================================
# - PromptVersionCreate : 새 프롬프트 본문 1~20000자, 공백만 입력하면 거절
class PromptVersionCreate(BaseModel):
    prompt_text: str = Field(min_length=1,max_length=20000)
    @field_validator('prompt_text')
    @classmethod
    def text_not_empty(cls, v):
        if not v.strip(): raise ValueError('프롬프트는 공백일 수 없습니다.')
        return v
# - PromptActivation : 활성화할 버전 번호 (1 이상)
class PromptActivation(BaseModel):
    version_no:int=Field(ge = 1)
# - ReindexRequest : 재색인 요청. force=True면 상태와 무관하게 재생성
class ReindexRequest(BaseModel):
    force:bool=False

# ============================================================
# 8. Intermediate I-01: 상세 6종 Pydantic 스키마
# ============================================================
# Intermediate I-01: 6종 상세 데이터별 Pydantic 검증(단순 dict 검사를 넘어 유형별 계약 고정).
from datetime import date,datetime
from pydantic import ConfigDict

# --------------------------------------------------------
# 상세 스키마 공통 부모
# --------------------------------------------------------
# 모든 문자열 필드에 공백값 금지 적용 (blockers·quality_notes는 빈 문자열 허용)
class DetailSchema(BaseModel):
    # extra='forbid': SRS에 없는 필드를 조용히 버리지 않고 오류로 처리합니다.
    model_config=ConfigDict(extra='forbid')

    @field_validator('*',mode='after')
    @classmethod
    def trim_nonempty(cls,value,info):
        if isinstance(value,str) and info.field_name not in ('blockers','quality_notes'):
            if not value.strip():raise ValueError(f'{info.field_name}: 공백값 불가')
        return value

# --------------------------------------------------------
# 카테고리별 상세 스키마
# --------------------------------------------------------
class ExperimentDetails(DetailSchema):
    experiment_date:date
    hypothesis:str=Field(min_length=1)
    result_summary:str=Field(min_length=1)

class DailyWorkDetails(DetailSchema):
    work_date:date
    progress:str=Field(min_length=1)
    blockers:str=''

class ResearchPlanDetails(DetailSchema):
    research_goal:str=Field(min_length=1)
    methodology:str=Field(min_length=1)
    target_date:date

class DataProcessingDetails(DetailSchema):
    dataset_name:str=Field(min_length=1)
    processing_steps:str=Field(min_length=1)
    quality_notes:str=''

class PromptDetails(DetailSchema):
    purpose:str=Field(min_length=1)
    prompt_text:str=Field(min_length=1,max_length=20000)

class MeetingDetails(DetailSchema):
    meeting_at:datetime
    attendees:str=Field(min_length=1)
    decisions:str=Field(min_length=1)

    @field_validator('meeting_at')
    @classmethod
    # 시간대 없는 시각 거절
    def requires_timezone(cls,value):
        if value.tzinfo is None:raise ValueError('meeting_at은 시간대 정보가 필요합니다.')
        return value

# 카테고리 코드 -> 상세 스키마 대응표
DETAIL_SCHEMAS={
    'EXPERIMENT':ExperimentDetails,'DAILY_WORK':DailyWorkDetails,
    'RESEARCH_PLAN':ResearchPlanDetails,'DATA_PROCESSING':DataProcessingDetails,
    'PROMPT':PromptDetails,'MEETING':MeetingDetails,
}
