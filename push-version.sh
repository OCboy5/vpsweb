#!/bin/bash

# Push version to GitHub as official release (v2.0 - with lessons learned)
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

# 1. Check if current branch is clean
if [ -n "$(git status --porcelain)" ]; then
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

# 5. Verify tag doesn't already exist remotely
if git ls-remote --tags origin | grep -q "refs/tags/$TAG$"; then
    echo "❌ Error: Tag $TAG already exists on GitHub."
    echo "   Choose a different version or delete the existing tag first."
    exit 1
fi

echo "✅ Pre-flight checks passed."

# Create annotated tag
echo "🏷️  Creating annotated tag..."
if [ -n "$RELEASE_NOTES" ]; then
    git tag -a "$TAG" -m "Release v$VERSION" -m "$RELEASE_NOTES"
else
    git tag -a "$TAG" -m "Release v$VERSION"
fi

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create tag $TAG"
    exit 1
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
    RELEASE_URL=$(gh release create "$TAG" --title "Release $VERSION" --notes "$RELEASE_NOTES")
else
    RELEASE_URL=$(gh release create "$TAG" --title "Release $VERSION" --notes "Release $VERSION")
fi

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create GitHub release"
    exit 1
fi

echo ""
echo "✅ Version ${VERSION} released successfully!"
echo "   📋 Tag: ${TAG}"
echo "   🔗 Release: $RELEASE_URL"
echo ""

# Verification
echo "🔍 Verifying release..."
gh release view "$TAG" --json tagName,isLatest > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Release verified on GitHub"
else
    echo "⚠️  Warning: Could not verify release on GitHub"
fi

echo ""
echo "🌐 View release at: $RELEASE_URL"