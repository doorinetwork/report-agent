"""비즈니스 오류는 키·SQL·원문을 메시지에 포함하지 않습니다."""

# ============================================================
# 오류 예외 클래스
# ============================================================
# 사용 예: DomainError(404, 'REPORT_NOT_FOUND', '요청한 보고서를 찾을 수 없습니다.')
# - status  : HTTP 상태코드 (예: 404, 422, 503)
# - code    : 오류 식별 코드 (예: REPORT_NOT_FOUND, VALIDATION_ERROR)
# - message : 사용자에게 보여 줄 한국어 메시지
# 주의: message에 API 키·SQL·보고서 원문을 넣지 않는다
class DomainError(Exception):
    def __init__(self,status:int,code:str,message:str):
        self.status,self.code,self.message=status,code,message
        super().__init__(message)
