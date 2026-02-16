#!/bin/bash

set -eo pipefail

# Check if VERSION environment is set
if [ -z "$VERSION" ]; then
  echo "ERROR: VERSION environment variable is not set"
  exit 1
fi

# If not triggered for local build, check for TWINE_PASSWORD
if [ -z "$LOCAL_BUILD" ]; then
  # Check if TWINE_PASSWORD is set
  if [ -z "$TWINE_PASSWORD" ]; then
    echo "ERROR: TWINE_PASSWORD environment variable is not set"
    exit 1
  fi
fi

rm -rf dist
rm -rf build
cat pyproject.toml | sed -i "s/version = \"[^\"]*\"/version = \"$VERSION\"/" pyproject.toml

# Install wheel
pip install wheel

# Build x86_64 wheel
rm -rf ./mariadb_table_usage/lib || true
mkdir -p ./mariadb_table_usage/lib
cd ./mariadb_table_usage_go
CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -o ../mariadb_table_usage/lib/mariadb_table_usage
cd ../
chmod +x ./mariadb_table_usage/lib/mariadb_table_usage
pip wheel . --no-deps --wheel-dir dist --config-settings="--build-option=--plat-name=manylinux2014_x86_64"

# Build arm64 wheel
rm -rf ./mariadb_table_usage/lib || true
mkdir -p ./mariadb_table_usage/lib
cd ./mariadb_table_usage_go
CGO_ENABLED=1 GOOS=linux GOARCH=arm64 CC=aarch64-linux-gnu-gcc go build -o ../mariadb_table_usage/lib/mariadb_table_usage
cd ../
chmod +x ./mariadb_table_usage/lib/mariadb_table_usage
pip wheel . --no-deps --wheel-dir dist --config-settings="--build-option=--plat-name=manylinux2014_aarch64"

# Remove the lib folder
rm -rf ./mariadb_table_usage/lib || true

if [ -z "$LOCAL_BUILD" ]; then
  pip install build twine
  twine upload ./dist/* --non-interactive
fi