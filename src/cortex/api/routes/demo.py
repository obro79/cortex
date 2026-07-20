from fastapi import APIRouter

from cortex.demo import DemoEvidenceControlPlane

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/evidence")
async def fixture_evidence() -> dict[str, object]:
    """Return the fixture-safe evidence summary used in the local demo."""
    report = await DemoEvidenceControlPlane().build_report()
    return report.as_dict()
