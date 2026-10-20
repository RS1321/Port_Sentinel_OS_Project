# API contract

## Terminal client

```bash
bash run.sh "What process is using port 8080?"
bash run.sh "What process is hogging port 8080? Stop it."
```

The default client requires the user service to be running. `--direct` executes the same planner and validation in the foreground. `--model MODEL` affects direct mode only. `--socket PATH` overrides the service socket for the client.

The CLI prints JSON. Process exit code zero means the request completed and returned a structured result; inspect `result.success` and `result.port_released` to determine whether a stop succeeded. Validation, model or transport exceptions return CLI exit code one. An occupied port with no unique visible owner produces a structured refusal and no signal.

## Python entry point

```python
from port_sentinel_agent import run_agent
answer = run_agent("What is listening on port 8080?")
print(answer)
```

`run_agent(user_prompt, model=MODEL, verbose=True)` returns a JSON string containing `plan` and `result`. `verbose` is retained for call-signature compatibility; the current implementation does not produce the old model/tool trace or a final prose response. Prompts must contain 1 to 4096 characters. This entry point invokes the local model directly, without the daemon transport.

The planner returns:

```json
{"action": "inspect", "port": 8080, "protocol": "tcp", "force": false}
```

Supported actions are `inspect`, `list`, and `stop`. Protocols are `tcp`, `udp`, and `all`. Port zero is allowed only for `list`. Stops require a specific numeric port and a single protocol. The application validates the plan against the original prompt before execution.

## Local request protocol

One UTF-8 JSON object terminated by a newline, one response per connection:

```json
{"prompt": "What process owns port 8080?"}
```

Successful response envelope:

```json
{"ok": true, "answer": "JSON-encoded plan and OS result"}
```

Failure envelope:

```json
{"ok": false, "error": "Error description"}
```

The request must contain only `prompt`. Transport requests are limited to 16384 bytes; clients impose a 1 MiB response limit. The service checks Unix peer credentials and handles requests serially. Model requests use a 60-second timeout; the client has a 90-second timeout.

## OS functions and native boundary

- `find_port_process(port, protocol="tcp")`: returns found status, socket records and visible process metadata.
- `list_listening_ports(protocol="all")`: returns TCP listeners and/or UDP bound sockets.
- `get_process_info(pid)`: returns existence, name, command line, UID and state.
- `process_identity(pid)`: reads Linux process start-time ticks.
- `kill_process(pid, signal_name="TERM", *, expected_start, port, protocol="tcp")`: requires expected identity and port, then rechecks current ownership before signalling. It cannot be called with the old two-argument signature in Review 2.

The C exports are `ps_open_process(int pid)` and `ps_signal_process(int descriptor, int signal_number)`. They return a descriptor or success code, or -1 with errno set. The Python binding converts native failures to exceptions. No numeric `os.kill` fallback is used when pidfd support or the native library is unavailable.
