from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from cortex.dev.workbench import DevWorkbenchError, DevWorkbenchService

router = APIRouter(prefix="/dev", tags=["dev"])


def get_workbench_service(request: Request) -> DevWorkbenchService:
    service = getattr(request.app.state, "dev_workbench", None)
    if not isinstance(service, DevWorkbenchService):
        raise HTTPException(status_code=404, detail="dev workbench is disabled")
    return service


def dev_error(error: DevWorkbenchError) -> HTTPException:
    return HTTPException(status_code=409, detail=error.as_dict())


@router.get("/workbench", response_class=HTMLResponse)
async def workbench(request: Request) -> str:
    return get_workbench_service(request).render_workbench_html()


@router.post("/fixtures/reset")
async def reset_fixtures(request: Request) -> dict[str, Any]:
    return get_workbench_service(request).reset()


@router.post("/fixtures/seed")
async def seed_fixtures(request: Request) -> dict[str, Any]:
    return get_workbench_service(request).seed()


@router.post("/pipeline/run")
async def run_pipeline(request: Request) -> dict[str, Any]:
    try:
        return await get_workbench_service(request).run_pipeline()
    except DevWorkbenchError as error:
        raise dev_error(error) from error


@router.get("/pipeline/runs/{run_id}")
async def get_pipeline_run(request: Request, run_id: str) -> dict[str, Any]:
    run = get_workbench_service(request).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="pipeline run not found")
    return run


@router.post("/retrieval/query")
async def query_retrieval(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    query = str(body.get("query", ""))
    if not query:
        raise HTTPException(status_code=422, detail="query is required")
    try:
        return get_workbench_service(request).query(query)
    except DevWorkbenchError as error:
        raise dev_error(error) from error


@router.get("/evidence-packs/{evidence_pack_id}")
async def get_evidence_pack(request: Request, evidence_pack_id: str) -> dict[str, Any]:
    evidence_pack = get_workbench_service(request).get_evidence_pack(evidence_pack_id)
    if evidence_pack is None:
        raise HTTPException(status_code=404, detail="evidence pack not found")
    return evidence_pack


@router.post("/evals/run")
async def run_evals(request: Request) -> dict[str, Any]:
    return get_workbench_service(request).run_evals()
