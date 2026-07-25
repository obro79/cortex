from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get("/workbench", response_class=PlainTextResponse)
async def workbench() -> str:
    return "Cortex dev workbench placeholder"
