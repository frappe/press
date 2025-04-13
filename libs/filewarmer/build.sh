#!/bin/bash

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

chmod +x build_helper.sh
docker build -f build.Dockerfile -t filewarmer-build-helper .
docker run --rm -it -v $(pwd):/app -w /app  -e VERSION="$VERSION" -e TWINE_PASSWORD="$TWINE_PASSWORD" filewarmer-build-helper ./build_helper.sh