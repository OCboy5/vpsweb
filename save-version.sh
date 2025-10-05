#!/bin/bash

# Version backup script for vpsweb
# Usage: ./save-version.sh <version>
# Example: ./save-version.sh 0.1.0

if [ -z "$1" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 0.1.0"
    exit 1
fi

VERSION=$1
DATE=$(date +%Y-%m-%d)
TAG="v${VERSION}-local-${DATE}"
BRANCH="backup-v${VERSION}-${DATE}"

echo "Saving version ${VERSION} locally..."
echo "Tag: ${TAG}"
echo "Branch: ${BRANCH}"

# Create local tag
git tag $TAG
if [ $? -ne 0 ]; then
    echo "Error: Failed to create tag ${TAG}"
    exit 1
fi

# Create backup branch
git checkout -b $BRANCH
if [ $? -ne 0 ]; then
    echo "Error: Failed to create branch ${BRANCH}"
    exit 1
fi

# Optionally push to remote (uncomment if you want remote backup)
# git push origin $TAG
# git push origin $BRANCH

# Return to main branch
git checkout main

echo ""
echo "✅ Version ${VERSION} saved successfully!"
echo "   Local tag: ${TAG}"
echo "   Backup branch: ${BRANCH}"
echo ""
echo "To restore from tag: git checkout ${TAG}"
echo "To restore from branch: git checkout ${BRANCH}"
echo "To list all versions: git tag -l '*local*'"