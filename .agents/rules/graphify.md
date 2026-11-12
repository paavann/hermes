---
trigger: always_on
description: Consult the graphify knowledge graph at graphify-out/ for codebase and architecture questions.
---

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- **When to Query**: For **cross-file or architectural questions** ("where is X used?", "how do A and B connect?"), when `graphify-out/graph.json` exists, first run `graphify query "<question>"` (CLI) or `query_graph` (MCP). Use `graphify path "<A>" "<B>"` / `shortest_path` for relationships and `graphify explain "<concept>"` / `get_node` for focused concepts. These return a scoped subgraph, usually much smaller than `GRAPH_REPORT.md` or raw grep output.
- **When to Skip**: If the user already specified the target file or asks about a single local function, read that file directly—skip `graphify query`.
- **Large Artifacts**: Read `graphify-out/GRAPH_REPORT.md` only for broad architecture reviews; never read `graphify-out/graph.json` directly.
- **Graph Updates**: - ONLY After modifying code files which involves structural cahnges in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)—skip for small body or style edits.
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context

