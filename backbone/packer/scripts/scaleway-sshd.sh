#!/bin/sh -eux

SSHD_CONFIG="/etc/ssh/sshd_config"

# ensure that there is a trailing newline before attempting to concatenate
sed -i -e '$a\' "$SSHD_CONFIG"

DISABLE_PASSWORD_AUTHENTICATION="PasswordAuthentication yes"
if grep -q -E "^[[:space:]]*PasswordAuthentication" "$SSHD_CONFIG"
then
    sed -i "s/^\s*PasswordAuthentication.*/${DISABLE_PASSWORD_AUTHENTICATION}/" "$SSHD_CONFIG"
else
    echo "$DISABLE_PASSWORD_AUTHENTICATION" >>"$SSHD_CONFIG"
fi
