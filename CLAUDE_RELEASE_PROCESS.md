# VPSWeb Release Process

This document outlines the standard procedure for creating a new release of the `vpsweb` application.

## Quick Reference

### Essential Commands

| Command                     | Description                                                                  |
| --------------------------- | ---------------------------------------------------------------------------- |
| `git checkout main`         | Switch to the main branch.                                                   |
| `git pull origin main`      | Update the local branch with the latest changes from the remote.             |
| `cp repository_root/repo.db repository_root/repo_backup_$(date +%Y%m%d_%H%M%S).db` | Create a timestamped backup of the database. |
| `poetry run pytest`         | Run the full test suite.                                                     |
| `poetry run black --check src/ tests/` | Check code formatting without making changes.                                    |
| `poetry run isort --check-only src/ tests/` | Check import order without making changes.                                   |
| `poetry run flake8 src/ tests/` | Lint the codebase for style and errors.                                      |
| `poetry run mypy src/`      | Run static type checking.                                                    |
| `./scripts/start.sh`        | Start the web application for manual verification.                           |
| `git commit -am "chore(release): vX.Y.Z"` | Commit all version and changelog updates.                                    |
| `./push-version.sh X.Y.Z "Release vX.Y.Z"` | Create and push a Git tag to trigger the GitHub Actions release workflow.      |
| `./save-version.sh X.Y.Z`   | Create a local backup tag for emergency rollbacks.                           |

### Files to Update

-   `pyproject.toml` (line 3): `version = "X.Y.Z"`
-   `src/vpsweb/__init__.py` (line 34): `__version__ = "X.Y.Z"`
-   `src/vpsweb/__main__.py` (line 343): `version="X.Y.Z"`
-   `CHANGELOG.md` (Add a new entry for the release)
-   `README.md` (Update any version references)

## Release Process

### Step 1: Preparation

1.  **Sync Repository**: Ensure your local `main` branch is synchronized with the remote repository.
    ```bash
    git checkout main
    git pull origin main
    ```

2.  **Backup Database**: Create a secure backup of the production database before making any changes.
    ```bash
    cp repository_root/repo.db repository_root/repo_backup_$(date +%Y%m%d_%H%M%S).db
    ```
    Verify that the backup file was created successfully.

3.  **Validate Version**: Check the current project version and confirm that the new version number follows semantic versioning (X.Y.Z).

### Step 2: Quality Assurance

1.  **Run Automated Checks**: Execute all automated quality gates. These checks mirror the CI/CD pipeline defined in `.github/workflows/ci.yml` and must pass before proceeding.
    ```bash
    poetry run pytest
    poetry run black --check src/ tests/
    poetry run isort --check-only src/ tests/
    poetry run flake8 src/ tests/
    poetry run mypy src/
    ```

2.  **WebUI Verification**: Start the web application and perform a quick manual check to ensure core functionality is working as expected.
    ```bash
    ./scripts/start.sh
    ```
    -   Access the Web UI at `http://127.0.0.1:8000`.
    -   Verify that the main page loads and basic operations can be performed.
    -   Test BBR functionality if time permits.

### Step 3: Release

1.  **Update Version Files**: Modify the version number in the files listed in the "Files to Update" section.

2.  **Update Changelog**: Add a new entry to `CHANGELOG.md` detailing the changes in this release.

3.  **Create Local Backup**: Create a local backup tag before making the release.
    ```bash
    ./save-version.sh X.Y.Z
    ```

4.  **Commit Changes**: Commit all the modifications with a standardized release message.
    ```bash
    git commit -am "chore(release): vX.Y.Z"
    ```

5.  **Create Release**: Execute the release script to create the tag and GitHub release.
    ```bash
    ./push-version.sh X.Y.Z "Release vX.Y.Z"
    ```

## Database Safety

-   **Location**: Database is located at `repository_root/repo.db`
-   **Never Commit the Database**: The `repository_root/repo.db` file is listed in `.gitignore` and must never be committed to the repository.
-   **Always Backup Before Release**: Create a timestamped backup before starting the release process using: `cp repository_root/repo.db repository_root/repo_backup_$(date +%Y%m%d_%H%M%S).db`
-   **Verify Backups**: Before proceeding with a release, confirm that the backup file was created successfully.
-   **Use Caution with `rm`**: Avoid using `rm` commands near the repository root directory.

## Emergency Rollback

If a critical issue is discovered after a release, use the local backup tag to revert the changes.

1.  **List Available Backup Tags**:
    ```bash
    git tag -l "*local*"
    ```

2.  **Checkout the Backup Tag**:
    ```bash
    git checkout vX.Y.Z-local-YYYY-MM-DD
    ```

3.  **Force Push to Main**: This is a destructive action and should only be performed in an emergency after coordinating with the team.
    ```bash
    git push origin -f main
    ```
