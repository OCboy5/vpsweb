##1 End-to-end Testing

# Set up environment
cp .env.example .env
# Edit .env and add your API keys

# Install in development mode
pip install -e .

# Run a test translation
vpsweb translate --input examples/poems/sample_en.txt \
  --source English --target Chinese -v

# Check the output
ls outputs/
cat outputs/translation_*.json

##2 Run Complete Test Suite

# Run all tests with coverage
pytest --cov=vpsweb --cov-report=html tests/

# Check coverage report
open htmlcov/index.html

# Run linting
black src/ tests/
flake8 src/ tests/

# Type checking (if using mypy)
mypy src/

##3 Prepare the project for initial release:

1. Review and update all version numbers in:
   - pyproject.toml
   - src/vpsweb/__init__.py (__version__)
   - config/default.yaml (workflow.version)

2. Create CHANGELOG.md with initial v0.1.0 entry

3. Add LICENSE file (MIT as specified in PSD)

4. Create a comprehensive examples/basic_usage.py showing:
   - Configuration loading
   - Programmatic API usage
   - Error handling

5. Final README.md polish with badges:
   - CI status
   - Coverage
   - License
   - Python versions

Ensure all files are properly formatted and documented.

##4 Final Commit and Tag

  # Add all files
  git add .

git config --global user.name "OCBoy5"
 
  # Initial commit
  git commit -m "feat: complete v0.1.0 implementation"

  # Set up remote (if not already done)
  git remote add origin <your-github-repo-url>

  # Push to main branch
  git push -u origin main

  # Create and push tag
  git tag -a v0.1.0 -m "Initial release - Vox Poetica Studio Web v0.1.0"
  git push origin v0.1.0

  # Create GitHub Release
  gh release create v0.1.0 --title "vpsweb v0.1.0" \
    --notes "Initial release of Vox Poetica Studio Web - Professional AI-powered poetry translation with 
  Translator→Editor→Translator workflow"


  ##5 local backup
  ./save-version.sh 0.1.0
  git tag -l "*local*"
  ./push-version.sh 0.2.0 "Added user authentication and new dashboard features"