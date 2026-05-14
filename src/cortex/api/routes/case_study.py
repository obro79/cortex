from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["case-study"])


@router.get("/case-study", response_class=HTMLResponse)
async def case_study() -> str:
    return render_case_study_html()


def render_case_study_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cortex Evidence Pack</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #18212a;
      --muted: #5a6876;
      --line: #d9e0e6;
      --paper: #fbfcfd;
      --panel: #ffffff;
      --teal: #087f7b;
      --amber: #a45f00;
      --red: #b42318;
      --green: #137333;
      --blue: #2457a6;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font: 15px/1.55 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
        sans-serif;
      overflow-x: hidden;
    }
    main {
      max-width: 1180px;
      min-width: 0;
      width: 100%;
      margin: 0 auto;
      padding: 28px 20px 48px;
    }
    header {
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
      gap: 24px;
      align-items: end;
      min-height: 380px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 24px;
    }
    header > * { min-width: 0; }
    h1, h2, h3, p { margin-top: 0; }
    h1 {
      max-width: 820px;
      font-size: clamp(44px, 7vw, 82px);
      line-height: 0.95;
      letter-spacing: 0;
      margin-bottom: 18px;
    }
    h2 { font-size: 26px; line-height: 1.2; margin-bottom: 12px; }
    h3 { font-size: 17px; line-height: 1.3; margin-bottom: 8px; }
    section { padding: 28px 0; border-bottom: 1px solid var(--line); }
    p, li, td { overflow-wrap: anywhere; }
    table { width: 100%; border-collapse: collapse; background: var(--panel); }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }
    th { color: var(--muted); font-weight: 650; }
    code, pre {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
    }
    pre {
      margin: 0;
      padding: 14px;
      overflow-x: auto;
      background: #111820;
      color: #eff7f5;
      border-radius: 8px;
      min-height: 130px;
    }
    .lede {
      color: var(--muted);
      max-width: 700px;
      font-size: 18px;
    }
    .pill-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 20px; }
    .pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 6px 10px;
      background: var(--panel);
      color: var(--muted);
      overflow-wrap: anywhere;
    }
    .hero-panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      min-width: 0;
    }
    .signal {
      display: grid;
      grid-template-columns: minmax(80px, 92px) minmax(0, 1fr);
      gap: 10px;
      padding: 10px 0;
      border-bottom: 1px solid var(--line);
    }
    .signal:last-child { border-bottom: 0; }
    .signal div:last-child { overflow-wrap: anywhere; }
    .label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
    .evidence-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }
    .tile {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      min-width: 0;
    }
    .metric { font-size: 28px; font-weight: 760; color: var(--teal); }
    .metric.warn { color: var(--amber); }
    .metric.block { color: var(--red); }
    .muted { color: var(--muted); }
    .architecture {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      overflow-x: auto;
    }
    .flow {
      display: grid;
      grid-template-columns: repeat(7, minmax(132px, 1fr));
      gap: 10px;
      min-width: 980px;
      align-items: stretch;
    }
    .node {
      border: 1px solid var(--line);
      border-top: 4px solid var(--teal);
      border-radius: 8px;
      background: #ffffff;
      padding: 12px;
      position: relative;
      min-height: 128px;
    }
    .node:after {
      content: ">";
      position: absolute;
      right: -10px;
      top: 48px;
      color: var(--muted);
      font-weight: 800;
    }
    .node:last-child:after { content: ""; }
    .node.events { border-top-color: var(--amber); }
    .node.storage { border-top-color: var(--green); }
    .node.gate { border-top-color: var(--red); }
    .node.output { border-top-color: var(--blue); }
    .node ul { margin: 8px 0 0; padding-left: 18px; color: var(--muted); }
    .steps { counter-reset: step; display: grid; gap: 10px; }
    .step {
      counter-increment: step;
      display: grid;
      grid-template-columns: 40px 1fr;
      gap: 12px;
      align-items: start;
    }
    .step:before {
      content: counter(step);
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: var(--ink);
      color: white;
      font-weight: 700;
    }
    .status-block {
      display: inline-block;
      color: white;
      background: var(--red);
      border-radius: 6px;
      padding: 2px 8px;
      font-weight: 760;
    }
    @media (max-width: 1080px) {
      header { grid-template-columns: 1fr; min-height: auto; }
      .grid, .evidence-grid { grid-template-columns: 1fr; }
      h1 { font-size: 48px; }
    }
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>Cortex</h1>
      <p class="lede">
        Evidence-aware knowledge infrastructure for engineering teams. Cortex
        turns Slack, Linear, GitHub, and repo-doc context into cited evidence
        packs and gates risky implementation work before an agent starts.
      </p>
      <div class="pill-row">
        <span class="pill">FastAPI</span>
        <span class="pill">Kafka/event envelopes</span>
        <span class="pill">Postgres source of truth</span>
        <span class="pill">Hybrid retrieval</span>
        <span class="pill">allow/warn/block gate</span>
      </div>
    </div>
    <aside class="hero-panel" aria-label="Demo proof summary">
      <div class="signal">
        <div class="label">Demo query</div>
        <div>What decisions constrain COR-123?</div>
      </div>
      <div class="signal">
        <div class="label">Evidence</div>
        <div>Slack decision, Linear issue, GitHub PR, diagram OCR, repo docs.</div>
      </div>
      <div class="signal">
        <div class="label">Gate</div>
        <div><span class="status-block">block</span> stale docs conflict with newer
        Postgres session decisions.</div>
      </div>
      <div class="signal">
        <div class="label">Artifact</div>
        <div>Public case study plus ADR-023 tradeoff record.</div>
      </div>
    </aside>
  </header>

  <section>
    <h2>Problem</h2>
    <p>
      Engineering context is scattered across Slack decisions, Linear tickets,
      GitHub PRs, repo docs, diagrams, and run logs. Agents and engineers miss
      old constraints, stale docs, and rollout blockers because the system of
      record is split across tools.
    </p>
  </section>

  <section>
    <h2>What I Built</h2>
    <div class="grid">
      <div class="tile">
        <div class="metric">6</div>
        <div class="muted">deterministic COR-123 source fixtures</div>
      </div>
      <div class="tile">
        <div class="metric">10</div>
        <div class="muted">pipeline stages from ingest to gate</div>
      </div>
      <div class="tile">
        <div class="metric warn">3</div>
        <div class="muted">explicit relationship seeds in the demo path</div>
      </div>
      <div class="tile">
        <div class="metric block">block</div>
        <div class="muted">context-gate result for stale conflicting docs</div>
      </div>
    </div>
  </section>

  <section>
    <h2>Architecture</h2>
    <div class="architecture" role="img"
      aria-label="Cortex architecture from connectors to evidence packs">
      <div class="flow">
        <div class="node">
          <h3>Connectors</h3>
          <ul>
            <li>Slack</li>
            <li>Linear</li>
            <li>GitHub</li>
            <li>Repo docs</li>
          </ul>
        </div>
        <div class="node events">
          <h3>Ingestion API</h3>
          <ul>
            <li>tenant context</li>
            <li>idempotency</li>
            <li>payload refs</li>
          </ul>
        </div>
        <div class="node events">
          <h3>Event Backbone</h3>
          <ul>
            <li>Kafka runtime</li>
            <li>event envelopes</li>
            <li>replay cursors</li>
          </ul>
        </div>
        <div class="node">
          <h3>Workers</h3>
          <ul>
            <li>normalize</li>
            <li>chunk + OCR</li>
            <li>embed + link</li>
          </ul>
        </div>
        <div class="node storage">
          <h3>Storage</h3>
          <ul>
            <li>Postgres records</li>
            <li>source chunks</li>
            <li>vector index</li>
          </ul>
        </div>
        <div class="node gate">
          <h3>Retrieval + Gate</h3>
          <ul>
            <li>cited evidence</li>
            <li>permission filters</li>
            <li>allow/warn/block</li>
          </ul>
        </div>
        <div class="node output">
          <h3>Evidence Pack</h3>
          <ul>
            <li>source links</li>
            <li>claims</li>
            <li>tradeoffs</li>
          </ul>
        </div>
      </div>
    </div>
  </section>

  <section>
    <h2>Core Flow</h2>
    <div class="steps">
      <div class="step">
        <p>Source event enters the ingestion API with workspace and tenant
        context.</p>
      </div>
      <div class="step">
        <p>Event is normalized into a replayable envelope and durable source
        record.</p>
      </div>
      <div class="step">
        <p>Workers persist records, chunk text, extract diagram OCR, create
        embeddings, and build deterministic links.</p>
      </div>
      <div class="step">
        <p>Retrieval merges lexical, vector, and relationship candidates while
        preserving citations.</p>
      </div>
      <div class="step">
        <p>Context gate returns allow, warn, or block with cited reasons and
        required human actions.</p>
      </div>
    </div>
  </section>

  <section>
    <h2>Evidence</h2>
    <div class="evidence-grid">
      <div class="tile">
        <h3>Retrieval Inspector</h3>
        <pre>query: COR-123 session migration constraints
providers: slack, linear, github, repo_docs
evidence_pack_id: ep-cor-123
expected_sources: 6
gate_status: block</pre>
      </div>
      <div class="tile">
        <h3>Context Gate</h3>
        <pre>status: block
risk_category: architecture_conflict
reason: stale repo docs conflict with newer
        Slack/GitHub/Linear session decisions
required_action: resolve Redis fallback rollout</pre>
      </div>
      <div class="tile">
        <h3>Worker Trace</h3>
        <pre>seed -> ingest -> kafka_event -> normalize
-> chunk_ocr -> embed -> index -> link
-> retrieve -> gate
trace_id: trace-run-cor-123-001</pre>
      </div>
      <div class="tile">
        <h3>Eval Output</h3>
        <pre>recall_at_k: 1.0
mrr: 1.0
citation_accuracy: 1.0
conflict_detection: 1.0
gate_accuracy: 1.0</pre>
      </div>
    </div>
  </section>

  <section>
    <h2>MCP Tool Surface</h2>
    <p>
      The MCP-facing surface is intentionally narrow: retrieve context, get
      related work, check the context gate, propose a canonical decision, and
      approve a canonical decision. The product claim is not "another chat UI."
      The claim is that agents get structured, cited context before they act.
    </p>
  </section>

  <section>
    <h2>Metrics</h2>
    <table>
      <thead>
        <tr><th>Metric</th><th>Current local proof</th><th>Resume-safe claim</th></tr>
      </thead>
      <tbody>
        <tr>
          <td>events replayed</td>
          <td>10 deterministic stages in the workbench trace</td>
          <td>Replayable pipeline shape, not production throughput</td>
        </tr>
        <tr>
          <td>chunks indexed</td>
          <td>6 COR-123 fixture chunks with citations</td>
          <td>Source-aware chunking and citation preservation</td>
        </tr>
        <tr>
          <td>retrieval p50/p95</td>
          <td>capture with local benchmark before publishing</td>
          <td>Only publish measured values</td>
        </tr>
        <tr>
          <td>context gate p50/p95</td>
          <td>capture with local benchmark before publishing</td>
          <td>Only publish measured values</td>
        </tr>
        <tr>
          <td>tests</td>
          <td>focused API, dev, retrieval, and context-gate suites</td>
          <td>Evidence-backed local validation</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>Tradeoffs</h2>
    <table>
      <thead>
        <tr><th>Choice</th><th>Why</th><th>Cost</th></tr>
      </thead>
      <tbody>
        <tr>
          <td>Event envelopes</td>
          <td>Make ingestion replayable and auditable across providers.</td>
          <td>More schema discipline and versioning overhead.</td>
        </tr>
        <tr>
          <td>Postgres source of truth</td>
          <td>Keep source records, chunks, gates, billing, and lifecycle state in
          one durable system.</td>
          <td>Needs careful indexing and async repository boundaries at scale.</td>
        </tr>
        <tr>
          <td>Cited retrieval</td>
          <td>Recruiters, engineers, and agents can inspect why a claim exists.</td>
          <td>Harder than plain semantic search because permissions and snippets
          must be preserved.</td>
        </tr>
        <tr>
          <td>allow/warn/block gate</td>
          <td>Keeps risky changes explainable instead of auto-taking action.</td>
          <td>Requires narrow rules, human resolution, and careful false-positive
          management.</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>What Breaks At 10x Scale</h2>
    <div class="grid">
      <div class="tile"><h3>Hot sources</h3><p class="muted">Slack and GitHub
      bursts need backpressure, cursor repair, and fair scheduling.</p></div>
      <div class="tile"><h3>Permission filtering</h3><p class="muted">Provider
      ACL snapshots must stay fresh without checking providers on every query.</p></div>
      <div class="tile"><h3>Stale embeddings</h3><p class="muted">Schema and
      model changes require index rebuilds and version-aware retrieval.</p></div>
      <div class="tile"><h3>Index rebuilds</h3><p class="muted">Derived indexes
      need replay plans so source truth does not fork from search state.</p></div>
    </div>
  </section>
</main>
</body>
</html>"""
