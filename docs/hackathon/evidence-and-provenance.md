# Evidence & provenance boundary

## Disclosure

This demo operates on a deterministic, synthetic fixture corpus. **NOT LIVE:**
no provider APIs, customer workspaces, OAuth tokens, or production indexes are
used. Provider names describe the fixture’s source shape, not an active
connection.

## Fixed inventory

| Source shape | Records | Notes |
| --- | ---: | --- |
| Slack | 3 | synthetic channel messages |
| Google Drive | 2 | synthetic documents |
| Linear | 2 | synthetic work items |
| GitHub | 1 | synthetic pull request / issue context |
| Jira | 1 | synthetic issue context |
| Repository docs | 1 | synthetic markdown context |
| **Total** | **10** | deterministic source records |

Three source records are media-source files. Their derived accessibility
artifacts are two captions and one transcript; these are derivatives, not
additional source records. The count is therefore 10 source records and three
media-derived artifacts.

## Evidence contract used in the demo

Each answer should be presented with: source label, source-type label, stable
fixture ID, short supporting excerpt, and a link or route to the originating
fixture view. The demo may describe this as a target evidence contract. It must
not imply that every provider currently exposes a live deep link or that a
ranked answer has been externally verified.

## What a judge can reproduce

1. Inspect the fixed counts in `assets/hackathon/scoreboard.svg`.
2. Run `python scripts/hackathon_evidence_report.py` to check the packet’s
   declared counts and mandatory disclosure language.
3. Follow the scripted search and evidence reveal in the run of show.

## Non-claims

- No assertion of live Slack, Google Drive, Linear, GitHub, Jira, or repository
  authentication.
- No assertion of realtime sync, comprehensive permissions enforcement, or
  customer data isolation from the fixture walkthrough.
- No quality benchmark beyond the controlled scripted scenario.
