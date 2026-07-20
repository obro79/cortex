# Cortex — Hackathon Demo Packet

Cortex is a production-shaped knowledge pipeline for turning fragmented work
context into traceable retrieval evidence. This hackathon packet demonstrates
the intended product experience using a **deterministic, synthetic fixture
corpus**. It is not a live customer deployment and it does not authenticate
against Slack, Google Drive, Linear, GitHub, Jira, or any external system.

## What the demo proves

- A source-neutral route from provider records through normalization, chunking,
  retrieval, and an evidence-backed answer.
- A reviewable answer surface: every assertion is meant to retain source and
  provenance context.
- A repeatable demo boundary: 10 synthetic records, including three
  media-source files, two captions, and one transcript.
- A safe MCP handoff boundary: `create_handoff_bundle` exports an opt-in,
  portable approved-summary/evidence-reference bundle and never accesses a
  Claude session.

The exact fixture inventory and its limitations are in
[docs/hackathon/evidence-and-provenance.md](docs/hackathon/evidence-and-provenance.md).
The architecture shown is a target/demo context, not a claim that every
component is live.

## Packet

- [Pitch](docs/hackathon/pitch.md) — concise narrative and judging criteria.
- [Demo run of show](docs/hackathon/demo-run-of-show.md) — operator script and
  recovery path.
- [Video shot list](docs/hackathon/video-shot-list.md) — 90-second recording plan.
- [Evidence and provenance](docs/hackathon/evidence-and-provenance.md) — fixture
  inventory, boundaries, and disclosure language.
- [Architecture plan](docs/hackathon/architecture-plan.md) and
  [100-ticket execution backlog](docs/hackathon/100-ticket-execution-backlog.md)
  — the retained durable target, phased build order, and ten explicit cleanup
  tickets.
- [Architecture context](assets/hackathon/architecture-context.svg) — a visual
  of the demo’s data and evidence flow.
- [Scoreboard](assets/hackathon/scoreboard.svg) — exact fixture counts, marked
  **NOT LIVE**.
- [Slides](deliverables/slides/cortex-hackathon-demo.pptx) — editable eight-slide
  deck in 16:9 format; regenerate it with the accompanying source and script.
- [Video package](deliverables/video/README.md) — a 72-second, no-audio teaser,
  plus narration, captions, storyboard, and checksum manifest.
- [Proof screenshots](deliverables/screenshots/README.md) — local proof-page
  captures whose displayed counts and **not live** boundary match the corpus.
- [`hackathon_demo_rehearsal.py`](scripts/hackathon_demo_rehearsal.py) — executes
  the local fixture seed → pipeline → query walkthrough without printing source
  bodies or URLs.

## Rebuild packet artifacts

```bash
node scripts/build_hackathon_scoreboard.mjs
node scripts/build_hackathon_deck.mjs
python scripts/hackathon_evidence_report.py
```

The deck builder uses only Node built-ins plus the system `zip` utility and
generates a standards-based `.pptx`; all slide copy is editable text and shape
objects. The report is a static consistency check of packet declarations, not
an integration test.

## Product repository quickstart

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy src
pytest
docker compose config
```

Run the API locally:

```bash
uvicorn cortex.api.app:create_app --factory --reload
```

## Demo and MCP rehearsal

Run the repeatable demo path with:

```bash
python scripts/hackathon_demo_rehearsal.py --format human
```

The local `cortex-mcp` executable speaks newline-delimited JSON-RPC over stdio.
Its handoff tool requires an approved summary; opaque handles require an
explicit `handoff_opt_in: true`. It returns `session_accessed: false` and marks
native Claude resume/fork unsupported rather than attempting session access.

## Honest status

The broader repository contains production-oriented contracts and phase work.
This packet deliberately makes no claim of live ingestion, live OAuth,
customer data, production retrieval quality, or provider completeness. Use the
fixture corpus for the hackathon story; validate integrations separately before
any production use. It also does not resume, fork, or inspect arbitrary Claude
sessions.
