#!/bin/bash

# Local backup script for vpsweb (v1.0 - Local backup system)
# Usage: ./save-version.sh <version>
# Example: ./save-version.sh 0.1.0

set -e  # Exit on any error

if [ -z "$1" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 0.1.0"
    exit 1
fi

VERSION=$1
DATE=$(date +%Y-%m-%d)
TAG="v${VERSION}-local-${DATE}"
BRANCH="backup-v${VERSION}-${DATE}"

echo "🔍 Running pre-flight checks..."

# 1. Check if current branch is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Error: You have uncommitted changes."
    echo "   Please commit or stash changes before creating a backup."
    echo "   Current changes:"
    git status --short
    exit 1
fi

# 2. Check if we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  Warning: You are not on main branch (current: $CURRENT_BRANCH)"
    echo "   It's recommended to create backups from main branch."
    echo "   Continue anyway? (y/N)"
    read -r response
    if [ "$response" != "y" ] && [ "$response" != "Y" ]; then
        echo "Backup cancelled."
        exit 1
    fi
fi

# 3. Check if tag already exists locally
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "❌ Error: Tag $TAG already exists locally."
    echo "   Choose a different version or delete the existing tag first."
    echo "   To delete: git tag -d $TAG"
    exit 1
fi

echo "✅ Pre-flight checks passed."
echo ""
echo "💾 Saving version ${VERSION} locally..."
echo "   Tag: ${TAG}"
echo "   Branch: ${BRANCH}"

# Create local tag
echo "🏷️  Creating local tag..."
git tag $TAG
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create tag ${TAG}"
    exit 1
fi
echo "✅ Tag ${TAG} created successfully"

# Create backup branch
echo "🌿 Creating backup branch..."
git checkout -b $BRANCH
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create branch ${BRANCH}"
    echo "🔧 Cleaning up failed tag..."
    git tag -d $TAG
    exit 1
fi
echo "✅ Branch ${BRANCH} created successfully"

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
echo "To list all local versions: git tag -l '*local*'"
echo "To list all versions: git tag -l 'v${VERSION}*'"