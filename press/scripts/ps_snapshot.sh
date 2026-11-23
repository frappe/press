#!/bin/sh
# Snapshot all processes (with PPID, full command line) to a timestamped file.
out="${1:-.}/ps-$(date +%F-%H%M%S).txt"
ps -eo user,pid,ppid,%cpu,%mem,stat,start,time,args ww > "$out" && echo "$out"
