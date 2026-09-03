from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import SessionDep
from app.modules.accounts.router import router as accounts_router
from app.modules.business_case.router import router as business_case_router
from app.modules.deployment.router import router as deployment_router
from app.modules.discovery.router import router as discovery_router
from app.modules.evaluation.router import router as evaluation_router
from app.modules.poc.router import router as poc_router
from app.modules.research.router import router as research_router
from app.modules.solutions.router import router as solutions_router

api_router = APIRouter()


@api_router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@api_router.get("/ready", tags=["system"])
def ready(session: SessionDep) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ready"}


api_router.include_router(accounts_router)
api_router.include_router(research_router)
api_router.include_router(discovery_router)
api_router.include_router(solutions_router)
api_router.include_router(poc_router)
api_router.include_router(business_case_router)
api_router.include_router(deployment_router)
api_router.include_router(evaluation_router)
