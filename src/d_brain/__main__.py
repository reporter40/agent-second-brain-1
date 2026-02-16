"""Entry point for running d-brain as a module."""

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point."""
    from d_brain.bot.main import run_bot
    from d_brain.config import get_settings
    from d_brain.services.git import VaultGit

    settings = get_settings()
    logger.info("d-brain starting...")
    logger.info("Vault path: %s", settings.vault_path)
    logger.info("Allowed users: %s", settings.allowed_user_ids or "all")

    # Ensure vault is synchronized
    if settings.vault_git_url:
        logger.info("Syncing vault from %s...", settings.vault_git_url)
        git = VaultGit(settings.vault_path)
        # Run sync in thread as it is blocking subprocess call
        try:
            await asyncio.to_thread(
                git.ensure_vault,
                git_url=settings.vault_git_url,
                branch=settings.vault_git_branch,
                token=settings.github_token,
            )
        except Exception as e:
            logger.error("Failed to sync vault: %s", e)
            # Decide if we should exit or continue. 
            # Continuing might be safer but user might lose data if they write to empty vault.
            # For now continue with warning.
    else:
        logger.warning("No VAULT_GIT_URL configured. Persistence is disabled!")

    await run_bot(settings)


if __name__ == "__main__":
    asyncio.run(main())
