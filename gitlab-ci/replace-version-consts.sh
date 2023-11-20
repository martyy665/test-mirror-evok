#!/bin/bash

function normalize_version_string(){
    echo "${1}" | sed 's/^[^0-9]*\([0-9]\+\.[0-9]\+\.[0-9]\+\).*$/\1/'
}

if [[ -n "${CI_COMMIT_TAG}" ]]; then
  echo "Version string before normalization: ${CI_COMMIT_TAG}"
  PACKAGE_VERSION=$(normalize_version_string "${CI_COMMIT_TAG}")
  echo "Version string after normalization: ${PACKAGE_VERSION}"
  export PACKAGE_VERSION
else
  PACKAGE_VERSION="$(/ci-scripts/generate-new-tag-for.sh .test.)"
  echo "Version string before normalization: ${PACKAGE_VERSION}"
  PACKAGE_VERSION=$(normalize_version_string "${PACKAGE_VERSION}")
  echo "Version string after normalization: ${PACKAGE_VERSION}"
  export PACKAGE_VERSION
fi

echo "Patching version constants with $PACKAGE_VERSION"

#Documentation markdown file used by web-interface of gitlab/github
sed -i "s/\\/evok\\/archive.*/\\/evok\\/archive\\/${PACKAGE_VERSION}.zip/" README.md
sed -i "s/unzip.*/unzip ${PACKAGE_VERSION}.zip/" README.md
sed -i "s/cd evok-.*/cd evok-${PACKAGE_VERSION}/" README.md
sed -i "s/version =.*/version = \"${PACKAGE_VERSION}\"/" pyproject.toml

#File for displaying version on http://<ip address>:<port>/version
echo "${PACKAGE_VERSION}" > version.txt
