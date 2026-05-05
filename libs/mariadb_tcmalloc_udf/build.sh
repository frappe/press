#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/dist"

MARIADB_VERSIONS=(10.4 10.6 11.8)

mkdir -p "${DIST_DIR}"

for version in "${MARIADB_VERSIONS[@]}"; do
    image="tcmalloc-udf-build:mariadb${version}"

    echo "==> MariaDB ${version}"

    docker build \
        --network=host \
        --build-arg "MARIADB_VERSION=${version}" \
        -t "${image}" \
        -f "${SCRIPT_DIR}/build.Dockerfile" \
        "${SCRIPT_DIR}"

    docker run --rm \
        -v "${DIST_DIR}:/out" \
        "${image}"
done

echo "Done. Output:"
ls -lh "${DIST_DIR}/"
