"""
# PURPOSE: Manages scheduled and manual updates of model data from Hugging Face

## INTERFACES:
- setup_scheduler(): Initializes the scheduler with daily updates
- refresh_models(specific_items: Optional[List] = None): Manually refresh specific models/users/searches
- check_for_updates(): Check for updates from followed creators

## DEPENDENCIES:
- apscheduler: Scheduling updates
- huggingface_hub: HF API interactions
"""

from datetime import datetime
from typing import List, Optional, Union
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from huggingface_hub import HfApi
from . import database


class UpdateScheduler:
    """
    PURPOSE: Handles scheduled and manual updates of model data
    """

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.scheduler = AsyncIOScheduler()
        self.hf_api = HfApi()
        self._setup_scheduler()

    def _setup_scheduler(self) -> None:
        """
        PURPOSE: Set up daily updates at 5 AM local time
        """
        self.scheduler.add_job(
            self.check_for_updates,
            CronTrigger(hour=5, minute=0),
            id="daily_update",
            replace_existing=True,
        )

    async def start(self) -> None:
        """
        PURPOSE: Start the scheduler
        """
        self.scheduler.start()

    async def stop(self) -> None:
        """
        PURPOSE: Stop the scheduler gracefully
        """
        self.scheduler.shutdown()

    async def check_for_updates(self) -> None:
        """
        PURPOSE: Check for updates from followed creators and update local cache
        """
        try:
            # Get list of followed creators
            async with database.get_connection(self.db_path) as db:
                creators = await db.execute("SELECT author FROM followed_creators")
                creator_list = [row[0] for row in await creators.fetchall()]

            # Update each creator's models
            for creator in creator_list:
                models = self.hf_api.list_models(author=creator)
                for model in models:
                    await database.upsert_model(self.db_path, model)

            # Update last checked timestamp
            now = datetime.now().isoformat()
            async with database.get_connection(self.db_path) as db:
                await db.execute(
                    "UPDATE followed_creators SET last_checked = ?", (now,)
                )
                await db.commit()

        except Exception as e:
            # Log error and continue - don't want to break the scheduler
            print(f"Error during update check: {e}")

    async def refresh_models(
        self,
        specific_items: Optional[List[str]] = None,
        item_type: str = "model",  # 'model', 'user', or 'search'
    ) -> None:
        """
        PURPOSE: Manually refresh specific models, users, or search results

        PARAMS:
        - specific_items: List of items to refresh (model IDs, usernames, or search queries)
        - item_type: Type of items to refresh ('model', 'user', or 'search')

        RETURNS: None
        """
        if item_type == "model" and specific_items:
            for model_id in specific_items:
                model_info = self.hf_api.model_info(model_id)
                await database.upsert_model(self.db_path, model_info)

        elif item_type == "user" and specific_items:
            for username in specific_items:
                models = self.hf_api.list_models(author=username)
                for model in models:
                    await database.upsert_model(self.db_path, model)

        elif item_type == "search" and specific_items:
            for query in specific_items:
                models = self.hf_api.list_models(search=query)
                for model in models:
                    await database.upsert_model(self.db_path, model)


async def create_scheduler(db_path: Union[str, Path]) -> UpdateScheduler:
    """
    PURPOSE: Factory function to create and start a scheduler

    PARAMS:
    - db_path: Path to the SQLite database

    RETURNS: Running UpdateScheduler instance
    """
    scheduler = UpdateScheduler(db_path)
    await scheduler.start()
    return scheduler
