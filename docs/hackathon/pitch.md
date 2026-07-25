# Cortex pitch

Work decisions are scattered across conversations, documents, tickets, code,
and media. The cost is not merely search time: teams lose the chain of evidence
behind a decision.

Cortex is the evidence-first context layer. It normalizes heterogeneous work
records into retrievable context, then presents an answer with the provenance
needed to inspect it. The product promise is simple: move from “I found a
sentence” to “I can see why this answer is supported.”

For this hackathon, Cortex demonstrates that flow with ten deterministic,
synthetic records spanning Slack (3), Google Drive (2), Linear (2), and one
each from GitHub, Jira, and repository docs. Three source files have two
captions and one transcript as derived accessibility artifacts. This is an
honest integration-shaped demo, **not a live connected workspace**.

Judges should evaluate four things: can one question cross source shapes; can
the answer expose evidence; can media-derived text join the evidence path; and
can the same demonstration be repeated without hidden provider state?

The final demo beat is an MCP `create_handoff_bundle`: an explicit,
portable approved-summary/evidence-reference handoff. It reports
`session_accessed: false` and intentionally does not offer native Claude
session resume or fork.
