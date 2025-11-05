#!/bin/bash

line_count=$(dmypy run press | wc -l)

MAX_ERRORS=813

if [ "$line_count" -gt $MAX_ERRORS ]; then
  echo "mypy shows $line_count errors, which exceeds the limit of $MAX_ERRORS."
  dmypy run "$@"
  exit 1
fi
