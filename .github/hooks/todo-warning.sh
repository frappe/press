#!/usr/bin/env bash

ORANGE='\033[0;33m'
NC='\033[0m'
BOLD='\033[1m'
NORMAL='\033[0m'


echo $GIT_COMMIT

check_file() {
    local file=$1
    local match_pattern=$2

    local file_changes_with_context=$(git diff -U999999999 -p --cached --color=always -- $file)
    local matched_additions=$(echo "$file_changes_with_context" | grep -C4 $'^\e\\[32m\+.*'"$match_pattern")

    if [ -n "$matched_additions" ]; then
        echo -e "${ORANGE}[WARNING]${NC} ${BOLD}$file${NORMAL} contains some $match_pattern."
        echo  "$matched_additions"
        echo -e "\n"
    fi
}


for file in `git diff --cached -p --name-status | cut -c3-`; do
    check_file $file 'TODO'
done
exit