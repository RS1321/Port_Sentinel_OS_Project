# Supplied report versions

Both PDF reports are included exactly as supplied by Rahul Sudarshan. Their diagrams, code listings and status statements describe the versions reviewed when those documents were prepared. They are historical review documents, not a live API reference.

| Report | Relationship to current code |
| --- | --- |
| [Review 1 PDF](Port_Sentinel_Agent_Review_1_Rahul_Sudarshan.pdf) | Describes the revised service, structured planner and C integration. Its test and GitHub-status statements are a snapshot from before publication. |
| [Review 2 PDF](Port_Sentinel_Agent_Review_2_with_diagrams.pdf) | Describes the original Python-only prototype, including a multi-turn tool-calling loop, REPL, `--quiet`, and numeric `os.kill` signalling. Those details do not describe the current service implementation. |

The current design differs from the earlier Review 2 in these ways:

- A per-user systemd daemon and terminal socket client provide the normal service path.
- The model returns a restricted JSON intent. The old eight-turn tool dispatcher and final prose answer are not used.
- A C source/header pair and ctypes binding signal pinned Linux process descriptors.
- Intent, same-user ownership, process identity, fresh socket ownership and observed port release are checked in application code.
- The CLI accepts one request per invocation; the old REPL and `--quiet` flag are absent.
- The kill function requires expected process identity and the requested port, rather than just PID and signal.

[The root README](../../README.md), [architecture](../ARCHITECTURE.md), [API contract](../API.md) and the source code describe current behaviour. GitHub Actions records automated Ubuntu build and integration results. Installed systemd and real-model demonstrations remain separate acceptance checks.

MCP is not implemented in either the historical prototype or the current code. Figures describing an MCP adapter are proposals only.
