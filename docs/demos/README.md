# Execution of Port Sentinel

[Watch or download the execution video](Port_Sentinel_Execution.mp4)

Duration: approximately 57 seconds. Format: 1280 x 720 H.264 MP4 at 15 frames per second, with consistent framing throughout.

This is a fresh command-based run of the Windows edition using Python 3.12.14 and the native C DLL. A local log viewer displays output from actual commands under the title "Execution of Port Sentinel".

## Execution shown

1. Run all 20 Windows tests successfully.
2. Start the authenticated named-pipe background user agent and check its status.
3. Start the disposable loopback TCP server on port 8080 (PID 36676 in this run).
4. Inspect the port and verify that the server remains running.
5. Independently confirm the listener with `netstat`.
6. Stop the server using the Windows C library's `TerminateProcess` operation.
7. Inspect again and check `netstat` to verify that the port is free.
8. Shut down the background agent and clean up the disposable test process.

The process ID varies between runs. Windows termination is forced; the recording uses a disposable server. This video documents the separate Windows edition supplied for the laptop demonstration; the repository's root implementation and installation instructions target Ubuntu.
