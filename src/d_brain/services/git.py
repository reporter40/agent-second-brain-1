"""Git automation service for vault."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class VaultGit:
    """Service for git operations on vault."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = Path(vault_path)

    def _run_git(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run git command in vault directory."""
        return subprocess.run(
            ["git", *args],
            cwd=self.vault_path,
            capture_output=True,
            text=True,
            check=False,
        )

    def get_status(self) -> str:
        """Get git status."""
        result = self._run_git("status", "--porcelain")
        return result.stdout

    def has_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        return bool(self.get_status().strip())

    def commit_changes(self, message: str) -> bool:
        """Stage all changes and commit.

        Args:
            message: Commit message

        Returns:
            True if commit was made, False otherwise
        """
        if not self.has_changes():
            logger.info("No changes to commit")
            return False

        # Stage all changes
        add_result = self._run_git("add", "-A")
        if add_result.returncode != 0:
            logger.error("Git add failed: %s", add_result.stderr)
            return False

        # Commit
        commit_result = self._run_git("commit", "-m", message)
        if commit_result.returncode != 0:
            logger.error("Git commit failed: %s", commit_result.stderr)
            return False

        logger.info("Committed: %s", message)
        return True

    def push(self) -> bool:
        """Push to remote.

        Returns:
            True if push was successful
        """
        result = self._run_git("push")
        if result.returncode != 0:
            logger.error("Git push failed: %s", result.stderr)
            return False

        logger.info("Pushed to remote")
        return True

    def commit_and_push(self, message: str) -> bool:
        """Commit all changes and push.

        Args:
            message: Commit message

        Returns:
            True if successful
        """
        if self.commit_changes(message):
            return self.push()
        return True  # No changes is not an error

    def ensure_vault(
        self, 
        git_url: str, 
        branch: str = "main", 
        token: str = "",
        username: str = "d-brain-bot",
        email: str = "bot@d-brain.local"
    ) -> bool:
        """Ensure vault is cloned and up to date.
        
        Args:
            git_url: Repository URL
            branch: Branch to use
            token: GitHub token for authentication
            username: Git user.name for commits
            email: Git user.email for commits
            
        Returns:
            True if successful
        """
        if not git_url:
            logger.warning("No git URL provided, skipping vault sync")
            return False

        # Prepare auth URL if token provided
        auth_url = git_url
        if token and "@" not in git_url:
            # Inject token into URL: https://TOKEN@github.com/...
            scheme, limit, path = git_url.partition("://")
            auth_url = f"{scheme}{limit}{token}@{path}"

        # Check if already cloned
        if not (self.vault_path / ".git").exists():
            logger.info("Cloning vault from %s...", git_url)
            # Ensure parent dir exists
            self.vault_path.mkdir(parents=True, exist_ok=True)
            
            # Clone
            result = subprocess.run(
                ["git", "clone", "--branch", branch, auth_url, "."],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                # If directory not empty, try cloning into temp and moving? 
                # For now just log error.
                logger.error("Git clone failed: %s", result.stderr)
                return False
            logger.info("Vault cloned successfully")
        else:
            logger.info("Vault already exists, pulling changes...")
            # Set remote url with token just in case
            self._run_git("remote", "set-url", "origin", auth_url)
            result = self._run_git("pull", "origin", branch)
            if result.returncode != 0:
                logger.error("Git pull failed: %s", result.stderr)
                return False
            logger.info("Vault updated")

        # Configure local git user
        self._run_git("config", "user.name", username)
        self._run_git("config", "user.email", email)
        
        return True
