# Cortex Agent Workflow

This project uses the local Garry Tan workflow repos checked out under
`/Users/owenfisher/Desktop/projects`:

- `gstack` for planning, review, QA, investigation, release, and browser-driven
  workflow discipline.
- `gbrain` for durable project memory, code lookup, notes, and cross-session
  context.

## Default Workflow

- Inspect this file and any future repo-local instructions before editing.
- Use gstack-style phases for non-trivial work:
  1. clarify scope and plan,
  2. implement narrowly,
  3. review the diff,
  4. run focused validation,
  5. summarize changes and remaining risks.
- Prefer gbrain lookup before broad manual code searches once this project has
  been indexed.
- Keep changes scoped. Do not modify unrelated files or user work.

## Local Paths

- GStack repo: `/Users/owenfisher/Desktop/projects/gstack`
- GBrain repo: `/Users/owenfisher/Desktop/projects/gbrain`
- Project path: `/Users/owenfisher/Desktop/projects/cortex`

## Useful Commands

```bash
# Run gbrain from the checked-out repo if it is not globally linked.
cd /Users/owenfisher/Desktop/projects/gbrain
bun run src/cli.ts query "what do we know about cortex?"

# Register/sync this project after files exist.
gbrain sources add cortex --path /Users/owenfisher/Desktop/projects/cortex
gbrain sync --source cortex --strategy code
```

## Notes

`cortex` may start as an empty project. Do not assume app structure until files
exist. If a git repo is initialized later, gstack team mode can be added with:

```bash
cd /Users/owenfisher/Desktop/projects/cortex
/Users/owenfisher/Desktop/projects/gstack/bin/gstack-team-init optional
```
