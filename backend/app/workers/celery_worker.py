from app.core.celery_app import celery_app

# Ensure task discovery when worker starts.
import app.workers.interview_tasks  # noqa: F401

__all__ = ['celery_app']
