#!/bin/bash

# Ensure ldd 2.27
ldd_version=$(ldd --version | head -n 1 | awk '{print $NF}')
if [[ "$ldd_version" == "2.27" ]]; then
    echo "ldd version is 2.27"
else
    echo "ldd version is NOT 2.27. Current version: $ldd_version"
fi

# Check if VERSION environment is set
if [ -z "$VERSION" ]; then
  echo "ERROR: VERSION environment variable is not set"
  exit 1
fi

# Check if TWINE_PASSWORD is set
if [ -z "$TWINE_PASSWORD" ]; then
  echo "ERROR: TWINE_PASSWORD environment variable is not set"
  exit 1
fi

rm -rf ./filewarmer/lib || true
mkdir -p ./filewarmer/lib
GOOS=linux GOARCH=amd64 go build -buildmode=c-shared -o ./filewarmer/lib/file_warmer_linux_amd64.so
GOOS=linux GOARCH=arm64 CC=aarch64-linux-gnu-gcc go build -buildmode=c-shared -o ./filewarmer/lib/file_warmer_linux_arm64.so
rm -rf dist
rm -rf build
cat setup.py | sed -i "s/version=\"[^\"]*\"/version=\"$VERSION\"/" setup.py
python3 setup.py sdist
ls -alh ./dist
twine upload dist/* --non-interactive