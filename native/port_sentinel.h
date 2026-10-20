#ifndef PORT_SENTINEL_H
#define PORT_SENTINEL_H
/* Returns a pinned process descriptor, or -1 with errno set. */
int ps_open_process(int pid);
/* Sends SIGTERM/SIGINT/SIGKILL through a pinned descriptor. */
int ps_signal_process(int descriptor, int signal_number);
#endif
