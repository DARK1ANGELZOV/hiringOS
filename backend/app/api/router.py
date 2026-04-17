from fastapi import APIRouter

from app.api.routes import admin, auth, candidates, documents, feedback, interviews, notifications, organizations, resumes, tests, users, vacancies

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(candidates.router)
api_router.include_router(documents.router)
api_router.include_router(resumes.router)
api_router.include_router(interviews.router)
api_router.include_router(interviews.ws_router)
api_router.include_router(feedback.router)
api_router.include_router(notifications.router)
api_router.include_router(tests.router)
api_router.include_router(admin.router)
api_router.include_router(users.router)
api_router.include_router(vacancies.router)
