CC     ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -fPIC
INC    ?= $(shell mariadb_config --include 2>/dev/null || mysql_config --cflags 2>/dev/null || echo "-I/usr/include/mysql")

.PHONY: all clean

all:
	$(CC) $(CFLAGS) $(INC) -shared -o tcmalloc_udf.so tcmalloc_udf.c -ldl

clean:
	rm -f tcmalloc_udf.so
