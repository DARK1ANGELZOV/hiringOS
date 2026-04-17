from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

HTTP_REQUESTS_TOTAL = Counter(
    'hiringos_http_requests_total',
    'Total HTTP requests',
    ['method', 'path', 'status'],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    'hiringos_http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'path'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)
AI_CLIENT_LATENCY_SECONDS = Histogram(
    'hiringos_ai_client_latency_seconds',
    'Latency for AI service client calls',
    ['operation', 'status'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 60),
)
UPLOAD_EVENTS_TOTAL = Counter(
    'hiringos_upload_events_total',
    'File upload events',
    ['result'],
)
REPORT_GENERATION_EVENTS_TOTAL = Counter(
    'hiringos_report_generation_events_total',
    'Interview report generation events',
    ['result'],
)
ANTI_CHEAT_SIGNALS_TOTAL = Counter(
    'hiringos_anti_cheat_signals_total',
    'Anti-cheat signals ingested',
    ['severity'],
)


def metrics_payload() -> bytes:
    return generate_latest()


def metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST
