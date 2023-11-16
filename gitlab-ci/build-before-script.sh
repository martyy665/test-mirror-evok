#!/bin/bash

# Set environment variables
. /ci-scripts/include.sh

# Fix default bob-preinstalled binary of virtualenv
# Replace it by the one from the package dh-virtualenv

UNWANTED_VIRTUALENV="/usr/local/bin/virtualenv"

if [ -x "${UNWANTED_VIRTUALENV}" ]; then
  echo "Removing unwanted virtualenv..."
  rm -f "${UNWANTED_VIRTUALENV}"
fi

apt update && apt install -y dh-virtualenv dh-python debhelper python3-all python3.11-dev dh-virtualenv dh-exec

. "$(pwd)/gitlab-ci/replace-version-consts.sh"

