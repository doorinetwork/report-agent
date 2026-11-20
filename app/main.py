"""보고서 처리 Agent 애플리케이션 진입점. 실행: python -m app.main"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text


# 사용자 모듈: DB 세션
from app.db.session import get_session_factory
# 사용자 모듈: errors
from app.services.errors import DomainError

# ============================================================
# FastAPI 앱 생성과 Router 등록
# ============================================================
app=FastAPI(title='Report Agent | 2026-11-20',version='1.0.0')


# ============================================================
# 오류 처리기
# ============================================================
# DomainError -> HTTP 상태코드 + 공통 오류 JSON
@app.exception_handler(DomainError)
def on_domain_error(request:Request,exc:DomainError):
    return JSONResponse(status_code=exc.status,
      content={'error':{'code':exc.code,'message':exc.message,'details':{}}})



# ============================================================
# [요구사항 B-01] API-00 Health 확인
# ============================================================
# - DB 연결 성공 + pgvector 확장 존재 : 200 {"status":"ok","db":"ready","vector":"ready"}
# - 그 밖의 모든 실패                 : 503 DB_UNAVAILABLE
@app.get('/health',tags=['System'])
def health():
    try:
        with get_session_factory()() as db:
            # DB 연결 확인
            db.execute(text('SELECT 1')).scalar_one()
            # pgvector 확장 설치 여부 확인
            exists=db.execute(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')")).scalar_one()
            if not exists:raise RuntimeError('pgvector extension missing')
        return {'status':'ok','db':'ready','vector':'ready'}
    except Exception:
        return JSONResponse(status_code=503,
           content={'error':{'code':'DB_UNAVAILABLE','message':'DB 또는 pgvector를 확인하세요.','details':{}}})

# ============================================================
# 서버 실행 진입점
# ============================================================
# 'app.main:app' : app/main.py 안의 app 객체를 실행 대상으로 지정
# host='127.0.0.1' : local IP address
# port=8000        : 접속 port // Postman base_url http://127.0.0.1:8000
# reload=False     : 코드 변경 시 자동 재시작하지 않음 (변경 후 직접 재시작)
def main():
    import uvicorn
    # 공통 main()은 완성. Core 구현은 app/api, services, repositories에 분리.
    uvicorn.run('app.main:app',host='127.0.0.1',port=8000,reload=False)

if __name__=='__main__':main()
