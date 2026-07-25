from __future__ import annotations

from html import escape
from typing import Any

from cortex.events.in_memory import InMemoryEventBus

from .evals import EvalRunner
from .evidence import EVIDENCE_PACK_ID, build_evidence_pack
from .fixtures import FixtureRepository
from .pipeline import FixturePipelineRunner
from .retrieval import DeterministicRetriever


class DevWorkbenchError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str | None = None,
        trace_id: str | None = None,
        fix: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.stage = stage
        self.trace_id = trace_id
        self.fix = fix

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "stage": self.stage,
            "trace_id": self.trace_id,
            "fix": self.fix,
        }


class DevWorkbenchService:
    def __init__(self) -> None:
        self.repository = FixtureRepository()
        self.event_bus = InMemoryEventBus()
        self.runs: dict[str, dict[str, Any]] = {}
        self.evidence_packs: dict[str, dict[str, Any]] = {}
        self.latest_query: dict[str, Any] | None = None
        self.latest_eval: dict[str, Any] | None = None
        self._run_count = 0

    def reset(self) -> dict[str, Any]:
        self.repository.reset()
        self.event_bus = InMemoryEventBus()
        self.runs.clear()
        self.evidence_packs.clear()
        self.latest_query = None
        self.latest_eval = None
        self._run_count = 0
        return {"status": "reset", "state": self.state_summary()}

    def seed(self) -> dict[str, Any]:
        summary = self.repository.seed()
        return {"status": "seeded", **summary}

    async def run_pipeline(self) -> dict[str, Any]:
        if not self.repository.seeded():
            raise DevWorkbenchError(
                "fixtures_not_seeded",
                "Seed deterministic fixtures before running the dev pipeline.",
                stage="seed",
                fix="POST /dev/fixtures/seed, then retry /dev/pipeline/run.",
            )
        self._run_count += 1
        runner = FixturePipelineRunner(self.repository, self.event_bus)
        run = await runner.run(self._run_count)
        self.runs[run["run_id"]] = run
        self.evidence_packs[EVIDENCE_PACK_ID] = build_evidence_pack(self.repository)
        return run

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        return self.runs.get(run_id)

    def query(self, query: str) -> dict[str, Any]:
        if not self.repository.seeded():
            raise DevWorkbenchError(
                "fixtures_not_seeded",
                "Seed deterministic fixtures before querying retrieval.",
                stage="retrieve",
                fix="POST /dev/fixtures/seed, then retry /dev/retrieval/query.",
            )
        result = DeterministicRetriever(self.repository).query(query)
        self.latest_query = result
        self.evidence_packs[EVIDENCE_PACK_ID] = build_evidence_pack(self.repository)
        return result

    def get_evidence_pack(self, evidence_pack_id: str) -> dict[str, Any] | None:
        if evidence_pack_id not in self.evidence_packs and self.repository.seeded():
            self.evidence_packs[EVIDENCE_PACK_ID] = build_evidence_pack(self.repository)
        return self.evidence_packs.get(evidence_pack_id)

    def run_evals(self) -> dict[str, Any]:
        if not self.repository.seeded():
            self.repository.seed()
        result = EvalRunner(DeterministicRetriever(self.repository)).run()
        self.latest_eval = result
        return result

    def state_summary(self) -> dict[str, Any]:
        latest_run = next(reversed(self.runs.values()), None) if self.runs else None
        return {
            "seeded": self.repository.seeded(),
            "fixture_counts": self.repository.summary()["counts"],
            "latest_run_id": latest_run["run_id"] if latest_run else None,
            "latest_run_status": latest_run["status"] if latest_run else None,
            "latest_gate_status": (
                self.latest_query["gate_status"] if self.latest_query else None
            ),
            "event_count": len(self.event_bus.list_events()),
            "evidence_pack_ids": sorted(self.evidence_packs),
        }

    def render_workbench_html(self) -> str:
        state = self.state_summary()
        latest_run = next(reversed(self.runs.values()), None) if self.runs else None
        stages = latest_run["stages"] if latest_run else []
        evidence_pack = self.evidence_packs.get(EVIDENCE_PACK_ID)
        eval_metrics = self.latest_eval["metrics"] if self.latest_eval else {}
        stage_rows = "\n".join(
            f"<tr><td>{escape(stage['stage'])}</td><td>{escape(stage['status'])}</td>"
            f"<td>{escape(stage['event_id'])}</td><td>{escape(stage['summary'])}</td></tr>"
            for stage in stages
        )
        citation_items = "\n".join(
            f"<li>{escape(citation['label'] or '')}</li>"
            for citation in (evidence_pack or {}).get("citations", [])
        )
        metric_items = "\n".join(
            f"<li>{escape(key)}: {value}</li>" for key, value in eval_metrics.items()
        )
        empty = (
            ""
            if state["seeded"]
            else (
                "<p>No fixtures seeded yet. Use the controls below to seed the "
                "COR-123 fixture bundle.</p>"
            )
        )
        gate = (
            (evidence_pack or {}).get("gate_result", {}).get("status")
            or state["latest_gate_status"]
            or "not_run"
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Cortex Dev Workbench</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; color: #172026; }}
    main {{ max-width: 1180px; margin: 0 auto; }}
    section {{ border-top: 1px solid #d5dce1; padding: 16px 0; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #e5eaee; padding: 8px; text-align: left; }}
    code {{ background: #eef3f5; padding: 2px 4px; border-radius: 4px; }}
    .gate {{ font-weight: 700; color: #a33b00; }}
  </style>
</head>
<body>
<main>
  <h1>Cortex Dev Workbench</h1>
  <p>Dev-only deterministic COR-123 fixture harness.</p>
  {empty}
  <section>
    <h2>Controls</h2>
    <button type="button" onclick="postJson('/dev/fixtures/seed')">
      Seed Fixtures
    </button>
    <button type="button" onclick="postJson('/dev/fixtures/reset')">Reset</button>
    <button type="button" onclick="postJson('/dev/pipeline/run')">Run Pipeline</button>
    <button type="button" onclick="queryRetrieval()">Query COR-123</button>
    <button type="button" onclick="postJson('/dev/evals/run')">Run Evals</button>
    <p>
      <input id="query" size="72"
        value="COR-123 session migration constraints">
    </p>
    <pre id="control-output" aria-live="polite"></pre>
  </section>
  <section>
    <h2>State</h2>
    <p>Seeded: <code>{state["seeded"]}</code></p>
    <p>Latest run: <code>{escape(str(state["latest_run_id"]))}</code></p>
    <p>Gate: <span class="gate">{escape(str(gate))}</span></p>
  </section>
  <section>
    <h2>Timeline</h2>
    <table><thead><tr><th>Stage</th><th>Status</th><th>Event</th><th>Summary</th></tr></thead>
    <tbody>{stage_rows}</tbody></table>
  </section>
  <section>
    <h2>Evidence Pack</h2>
    <p>ID: <code>{escape(EVIDENCE_PACK_ID)}</code></p>
    <ul>{citation_items}</ul>
  </section>
  <section>
    <h2>Eval Metrics</h2>
    <ul>{metric_items}</ul>
  </section>
</main>
<script>
async function postJson(path, body = {{}}) {{
  const output = document.getElementById('control-output');
  const response = await fetch(path, {{
    method: 'POST',
    headers: {{'content-type': 'application/json'}},
    body: JSON.stringify(body)
  }});
  const data = await response.json();
  output.textContent = JSON.stringify(data, null, 2);
}}
async function queryRetrieval() {{
  const query = document.getElementById('query').value;
  await postJson('/dev/retrieval/query', {{query}});
}}
</script>
</body>
</html>"""
