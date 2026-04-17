from contextlib import asynccontextmanager
from time import perf_counter
from uuid import UUID

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.core.limiter import limiter
from app.core.logging import configure_logging
from app.core.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL, metrics_content_type, metrics_payload
from app.core.security import decode_access_token
from app.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['*'],
)


@app.middleware('http')
async def audit_request(request: Request, call_next):
    started = perf_counter()
    response = await call_next(request)
    duration = perf_counter() - started

    path = request.url.path
    method = request.method.upper()
    status_code = str(response.status_code)
    HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=status_code).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration)

    if request.url.path in {'/healthz', '/readyz', '/metrics'}:
        return response

    user_id = None
    auth_header = request.headers.get('authorization', '')
    token = None
    if auth_header.startswith('Bearer '):
        token = auth_header.removeprefix('Bearer ').strip()
    if not token:
        token = request.cookies.get(settings.access_cookie_name)

    if token:
        try:
            payload = decode_access_token(token)
            sub = payload.get('sub')
            if sub:
                user_id = UUID(sub)
        except Exception:
            user_id = None

    try:
        async with SessionLocal() as session:
            audit_service = AuditService(AuditRepository(session))
            await audit_service.log(
                action=f'http.{request.method.lower()}',
                user_id=user_id,
                entity_type='route',
                entity_id=request.url.path,
                metadata_json={'status_code': response.status_code},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get('user-agent'),
            )
            await session.commit()
    except Exception:
        # Never block API response on audit write failure.
        pass

    return response


@app.get('/healthz')
async def healthz():
    return {'status': 'ok'}


@app.get('/readyz')
async def readyz():
    return {'status': 'ready'}


@app.get('/metrics')
async def metrics():
    return Response(content=metrics_payload(), media_type=metrics_content_type())


app.include_router(api_router, prefix=settings.api_prefix)
