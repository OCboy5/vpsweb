#!/bin/bash

# Push version to GitHub as official release
# Usage: ./push-version.sh <version> [release_notes]
# Example: ./push-version.sh 0.1.0 "Initial release with basic functionality"

if [ -z "$1" ]; then
    echo "Usage: $0 <version> [release_notes]"
    echo "Example: $0 0.1.0 'Initial release'"
    echo "Example: $0 0.2.0"
    exit 1
fi

VERSION=$1
RELEASE_NOTES=$2
TAG="v${VERSION}"

echo "Pushing version ${VERSION} to GitHub..."
echo "Tag: ${TAG}"

# Check if current branch is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Warning: You have uncommitted changes."
    echo "   Please commit or stash changes before creating a release."
    read -p "   Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if tag already exists locally
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "⚠️  Warning: Tag $TAG already exists locally."
    read -p "   Overwrite existing tag? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git tag -d "$TAG"
        echo "   Deleted existing local tag"
    else
        echo "   Release cancelled."
        exit 1
    fi
fi

# Check if tag already exists on remote
if git ls-remote --tags origin | grep -q "refs/tags/$TAG$"; then
    echo "⚠️  Warning: Tag $TAG already exists on GitHub."
    read -p "   Overwrite remote tag? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin :refs/tags/"$TAG" 2>/dev/null || true
        echo "   Deleted existing remote tag"
    else
        echo "   Release cancelled."
        exit 1
    fi
fi

# Create annotated tag with release notes
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
echo "Pushing current commits..."
git push origin main
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to push commits to origin"
    exit 1
fi

# Push the tag
echo "Pushing tag to GitHub..."
git push origin "$TAG"
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to push tag to origin"
    exit 1
fi

echo ""
echo "✅ Version ${VERSION} pushed successfully to GitHub!"
echo "   Tag: ${TAG}"
echo "   GitHub will automatically create a draft release for this tag."
echo ""
echo "View your release at: https://github.com/$(git config --get remote.origin.url | sed 's/.*://;s/\.git$//')/releases"

# Optional: Open GitHub releases page in browser
read -p "Open GitHub releases page in browser? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    REPO_URL=$(git config --get remote.origin.url | sed 's/.*://;s/\.git$//')
    open "https://github.com/$REPO_URL/releases" 2>/dev/null || echo "Could not open browser"
fi