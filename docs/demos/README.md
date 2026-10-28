# Windows 11 execution recording

[Watch or download Port_Sentinel_Windows11_Demo.mp4](Port_Sentinel_Windows11_Demo.mp4)

- Duration: approximately 75 seconds; 1280 x 720 H.264 MP4; no narration.
- Environment: Windows 11, Python 3.12.14 and the Windows C DLL.
- Mode: explicit command mode. The OpenAI API check returned HTTP 429, so this video does not demonstrate successful English interpretation.
- Capture: a real-time local log viewer displays output from actual Windows subprocesses. It is not a native PowerShell window or an Ubuntu recording.

## Execution shown

1. Run all 20 Windows tests successfully.
2. Start the authenticated named-pipe background user agent and check its status.
3. Start the disposable loopback TCP server on port 8080 (PID 36236 in this run).
4. Inspect the port and verify that the server remains running.
5. Independently confirm the listener with `netstat`.
6. Stop the server using the Windows C library's `TerminateProcess` operation.
7. Inspect again and check `netstat` to verify that the port is free.
8. Shut down the background agent and clean up the disposable test process.

The process ID varies between runs. Windows termination is forced; the recording uses a disposable server. This video documents the separate Windows edition supplied for the laptop demonstration; the repository's root implementation and installation instructions target Ubuntu.
