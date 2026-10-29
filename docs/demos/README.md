# Execution of Port Sentinel

[Watch or download the execution video](Port_Sentinel_Gemini_Execution.mp4)

Duration: approximately 51 seconds. Format: 1280 x 720 H.264 MP4 at 15 frames per second, with consistent framing throughout.

This is a fresh run of the Windows edition using Google Gemini (gemini-3.5-flash-lite), Python 3.12.14 and the native C DLL. Two real API requests translate English into validated inspect/stop plans. A local log viewer displays actual command output under the title "Execution of Port Sentinel". No API key appears in the video or these files.

## Execution shown

1. Run all 24 Windows tests successfully.
2. Start the authenticated named-pipe background user agent and check its status.
3. Start the disposable loopback TCP server on port 8080 (PID 9272 in this run).
4. Ask "What process is using port 8080?" through Gemini, inspect the returned PID, and verify that the server remains running.
5. Independently confirm the listener with `netstat`.
6. Ask "What process is hogging port 8080? Stop it." through Gemini. Validate the stop plan and terminate the demo server through the C library's `TerminateProcess` operation.
7. Inspect again and check `netstat` to verify that the port is free.
8. Shut down the background agent and clean up the disposable test process.

The process ID varies between runs. Windows termination is forced; the recording uses a disposable server. This video documents the separate Windows edition supplied for the laptop demonstration; the repository's root implementation and installation instructions target Ubuntu.

Four Gemini unit tests use mocked network responses to check validation and error sanitisation. The two English requests in the recorded demonstration call Google's API separately using the saved environment variable.
