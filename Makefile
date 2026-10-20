CC = cc
CFLAGS = -O2 -Wall -Wextra -Werror -fPIC

all: native/libport_sentinel.so

native/libport_sentinel.so: native/port_sentinel.c native/port_sentinel.h
	$(CC) $(CFLAGS) -shared -o $@ native/port_sentinel.c

test: all
	python3 -m unittest discover -s tests -v

.PHONY: all test
