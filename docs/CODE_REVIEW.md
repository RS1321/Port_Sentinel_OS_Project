# Review findings and corrections

Reviewed input: port_sentinel_agent.tar.gz, seven files, supplied by Rahul Sudarshan. Original archive retained unchanged outside the corrected project.

## Findings in the original

1. Missing requirement: no background service, daemon entry point or systemd unit. `run.sh` started a foreground Python program only.
2. Missing requirement: no C source, header, build configuration or Python/C binding. Python's native implementation alone does not fulfil the requested explicit C files.
3. Parsing defect: combined `ss -lntup` output can include a leading Netid column. The fixed column positions could parse the queue as a local address and drop the record.
4. Partial data defect: one row with a PID caused an early return, preventing enrichment of other rows with missing owners.
5. Fallback defect: `/proc` reported every local address as a wildcard rather than decoding IPv4/IPv6 addresses.
6. Safety defect: the tool dispatcher accepted any model-supplied PID. Resolve-first and destructive-intent rules existed in prose only, without application enforcement.
7. Race concern: direct numeric `os.kill` had no process-identity or port-owner revalidation.
8. Result defect: successful signal delivery was treated as completion, without checking port release.
9. Test gap: one fixed-port script lacked parser, intent, ambiguous-owner, timeout, native and service tests.
10. Documentation mismatch: README safety claims were stronger than code enforcement. No actual MCP transport was present.

## Revised implementation

Added a per-user systemd service, restricted Unix socket transport, structured local-model planner, deterministic intent validation and a C pidfd library with Python ctypes bindings. Corrected ss parsing and per-row owner supplementation, decoded proc addresses, added timeout fallback, same-user restrictions and port-release verification. Replaced the fixed-port smoke script with standard-library regression tests and provided Ubuntu CI and manual acceptance instructions.

Supported natural language is intentionally bounded: one numeric port, an explicit inspect/list/stop intent, TCP by default, explicit UDP when required, and explicit force for KILL. Negation and conditional destructive requests are refused. This is a project prototype; the checks are not a proof that every possible English sentence is interpreted safely.

## Evidence

29 tests discovered on Windows: 25 passed, 4 Linux integration tests skipped. Python modules compile successfully. This local log does not establish Ubuntu, native compilation, real-model or installed systemd execution. Linux build and integration results are recorded separately by GitHub Actions. Test output is included in docs/test-results-windows.txt. The repository now contains the corrected source, reports and an Ubuntu validation workflow. See the latest GitHub Actions run for Linux test results.

## Remaining constraints

No stop of other users' processes, no automatic privilege elevation, no automatic KILL, no cross-namespace discovery, no resource-usage profiling and no MCP implementation. Socket ownership can change in the small interval before signal delivery; pinned pidfds prevent PID reuse from redirecting the signal but cannot freeze socket state. Local model memory/latency is additional to the daemon. Authentication protects against other UIDs, not hostile software already running under the same UID.
