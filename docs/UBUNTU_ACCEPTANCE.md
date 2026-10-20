# Ubuntu acceptance checklist

Status on 20 October 2026: pending. Run on a disposable Ubuntu user account.

1. Record Ubuntu release, kernel, Python, compiler, systemd and Ollama/model versions.
2. Run `make` and `make test`; save compiler output and unittest output. Confirm all Linux tests execute, not skip.
3. Install requirements and start the local Ollama model. Use direct inspect against a disposable listener. Confirm the reported PID matches the child.
4. Start the user service. Confirm `systemctl --user is-active port-sentinel.service` returns active, runtime directory mode is 0700, socket mode is 0600 and journald records requests.
5. Send the exact example prompt through `bash run.sh`. Confirm TERM, child exit and port release. Repeat an inspect-only request first to ensure it does not stop the child.
6. Try a nonexistent port, UDP socket, IPv6 listener, malformed input, multiple-owner socket and hidden-owner socket. Confirm no unrelated process is signalled.
7. Send a negative stop request and an inspect request with an intentionally incorrect stop plan in a unit test. Both must refuse execution.
8. Stop/restart the service and verify socket cleanup and reconnection. Test model unavailability and malformed model output; the CLI should report an error and the service remain alive.
9. Force-stop only a disposable child that ignores TERM. Verify TERM does not claim release, then explicitly request force and verify release.
10. If logout persistence is required, enable lingering, log out/in and confirm user-service behaviour. Do not mark this checked from a terminal-only daemon test.

Record actual results and failures with dates. Expected results in README are not evidence of execution.
