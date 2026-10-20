#define _GNU_SOURCE
#include "port_sentinel.h"
#include <errno.h>
#include <signal.h>
#include <sys/syscall.h>
#include <unistd.h>

int ps_open_process(int pid) {
    if (pid <= 2 || pid == getpid() || pid == getppid()) {
        errno = EPERM;
        return -1;
    }
    return (int)syscall(SYS_pidfd_open, pid, 0);
}

int ps_signal_process(int descriptor, int signal_number) {
    if (descriptor < 0 || (signal_number != SIGTERM &&
        signal_number != SIGINT && signal_number != SIGKILL)) {
        errno = EINVAL;
        return -1;
    }
    return (int)syscall(SYS_pidfd_send_signal, descriptor, signal_number, NULL, 0);
}
