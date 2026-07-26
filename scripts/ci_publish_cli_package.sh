#!/usr/bin/env bash
set -euo pipefail

archive="cli/dist/agents-tools-cli-linux-amd64-${CI_COMMIT_TAG}.tar.gz"
tar -C cli/dist -czf "$archive" agents-tools
curl --fail --header "JOB-TOKEN: $CI_JOB_TOKEN" --upload-file "$archive" "${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/generic/agents-tools-cli/${CI_COMMIT_TAG}/agents-tools-cli-linux-amd64-${CI_COMMIT_TAG}.tar.gz"
