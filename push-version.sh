#!/bin/bash

# Push version to GitHub as official release (v3.0 - v0.2.1 improvements)
# Usage: ./push-version.sh <version> [release_notes]
# Example: ./push-version.sh 0.1.0 "Initial release with basic functionality"

set -e  # Exit on any error

if [ -z "$1" ]; then
    echo "Usage: $0 <version> [release_notes]"
    echo "Example: $0 0.1.0 'Initial release'"
    echo "Example: $0 0.2.0"
    exit 1
fi

VERSION=$1
RELEASE_NOTES=$2
TAG="v${VERSION}"

echo "🚀 Pushing version ${VERSION} to GitHub..."
echo "   Tag: ${TAG}"

# Pre-flight checks
echo "🔍 Running pre-flight checks..."

# 1. Check if current branch is clean (ignore untracked files that are properly ignored)
if [ -n "$(git status --porcelain | grep -v '^\?\?')" ]; then
    echo "❌ Error: You have uncommitted changes."
    echo "   Please commit or stash changes before creating a release."
    echo "   Current changes:"
    git status --short
    exit 1
fi

# 2. Check if we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "❌ Error: You must be on main branch to create a release."
    echo "   Current branch: $CURRENT_BRANCH"
    echo "   Switch to main branch with: git checkout main"
    exit 1
fi

# 3. Check if GitHub CLI is available
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed."
    echo "   Install it from: https://cli.github.com/"
    exit 1
fi

# 4. Check if we're authenticated with GitHub
if ! gh auth status &> /dev/null; then
    echo "❌ Error: GitHub CLI authentication required."
    echo "   Run: gh auth login"
    exit 1
fi

# 5. Check if tag already exists remotely
if git ls-remote --tags origin | grep -q "refs/tags/$TAG$"; then
    echo "ℹ️  Tag $TAG already exists on GitHub."
    echo "   This is normal if you're re-pushing an existing release."
    echo "   The script will continue and update the release if needed."

    # Check if release exists
    if gh release view "$TAG" >/dev/null 2>&1; then
        echo "ℹ️  Release $TAG already exists on GitHub."
        echo "   Skipping release creation."
        echo "   📋 Existing release: https://github.com/OCboy5/vpsweb/releases/tag/$TAG"
        exit 0
    fi
fi

echo "✅ Pre-flight checks passed."

# Create annotated tag (handle case where tag already exists locally)
echo "🏷️  Creating annotated tag..."
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "ℹ️  Tag $TAG already exists locally, skipping tag creation"
else
    if [ -n "$RELEASE_NOTES" ]; then
        git tag -a "$TAG" -m "Release v$VERSION" -m "$RELEASE_NOTES"
    else
        git tag -a "$TAG" -m "Release v$VERSION"
    fi

    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to create tag $TAG"
        exit 1
    fi
    echo "✅ Tag $TAG created successfully"
fi

# Push current commits first (to ensure tag has a target)
echo "📤 Pushing current commits..."
git push origin main
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to push commits to origin"
    exit 1
fi

# Push the tag
echo "📤 Pushing tag to GitHub..."
git push origin "$TAG"
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to push tag to origin"
    exit 1
fi

# Create GitHub release using CLI (more reliable than GitHub Actions)
echo "🎉 Creating GitHub release..."
if [ -n "$RELEASE_NOTES" ]; then
    RELEASE_URL=$(gh release create "$TAG" --title "Release $VERSION" --notes "$RELEASE_NOTES" 2>/dev/null)
else
    RELEASE_URL=$(gh release create "$TAG" --title "Release $VERSION" --notes "Release $VERSION" 2>/dev/null)
fi

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create GitHub release automatically"
    echo "🔧 Possible causes:"
    echo "   - Insufficient GitHub permissions"
    echo "   - Release already exists"
    echo "   - Network connectivity issues"
    echo ""
    echo "👍 Manual creation instructions:"
    echo "   1. Visit: https://github.com/OCboy5/vpsweb/releases/new"
    echo "   2. Tag: $TAG"
    echo "   3. Title: Release $VERSION"
    echo "   4. Copy/paste release notes if provided"
    echo ""
    echo "   Or use GitHub CLI:"
    echo "   gh release create $TAG --title 'Release $VERSION' --notes 'Your release notes here'"
    exit 1
fi

echo ""
echo "✅ Version ${VERSION} released successfully!"
echo "   📋 Tag: ${TAG}"
echo "   🔗 Release: $RELEASE_URL"
echo ""

# Verification
echo "🔍 Verifying release..."
gh release view "$TAG" --json tagName > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Release verified on GitHub"
else
    echo "⚠️  Warning: Could not verify release on GitHub"
fi

echo ""
echo "🌐 View release at: $RELEASE_URL"