from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

AI_HTTP_REQUESTS_TOTAL = Counter(
    'hiringos_ai_http_requests_total',
    'Total AI service HTTP requests',
    ['method', 'path', 'status'],
)
AI_HTTP_REQUEST_DURATION_SECONDS = Histogram(
    'hiringos_ai_http_request_duration_seconds',
    'AI service request duration in seconds',
    ['method', 'path'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 60),
)
AI_RESUME_PARSE_EVENTS_TOTAL = Counter(
    'hiringos_ai_resume_parse_events_total',
    'Resume parser outcomes',
    ['result'],
)


def metrics_payload() -> bytes:
    return generate_latest()


def metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST
