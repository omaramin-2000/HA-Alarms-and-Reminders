"""Storage handling for Alarms and Reminders."""
import logging
from typing import Dict, Any
import json
from pathlib import Path
import asyncio
import aiofiles

from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.util import dt as dt_util
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

class AlarmReminderStorage:
    """Class to handle storage of alarms and reminders."""

    def __init__(self, hass: HomeAssistant):
        """Initialize storage."""
        self.hass = hass
        self.storage_dir = Path(hass.config.path(".storage"))
        self.alarms_file = self.storage_dir / "alarms_and_reminders.alarms.json"
        self.reminders_file = self.storage_dir / "alarms_and_reminders.reminders.json"
        self._items = {
            "alarms": {
                "active": {},
                "scheduled": {},
                "stopped": {}
            },
            "reminders": {
                "active": {},
                "scheduled": {},
                "stopped": {}
            }
        }
        self._lock = asyncio.Lock()

    async def async_load(self) -> Dict[str, Dict[str, Any]]:
        """Load items from storage."""
        try:
            async with self._lock:
                flattened_items = {}
                
                # Load alarms
                if self.alarms_file.exists():
                    async with aiofiles.open(self.alarms_file, 'r') as f:
                        content = await f.read()
                        alarms_data = json.loads(content)
                        self._items["alarms"] = alarms_data
                        # Flatten active items for coordinator
                        for status in ["active", "scheduled", "stopped"]:
                            flattened_items.update(alarms_data[status])

                # Load reminders
                if self.reminders_file.exists():
                    async with aiofiles.open(self.reminders_file, 'r') as f:
                        content = await f.read()
                        reminders_data = json.loads(content)
                        self._items["reminders"] = reminders_data
                        # Flatten active items for coordinator
                        for status in ["active", "scheduled", "stopped"]:
                            flattened_items.update(reminders_data[status])

                # Convert datetime strings to objects
                for item_id, data in flattened_items.items():
                    if "scheduled_time" in data:
                        data["scheduled_time"] = dt_util.parse_datetime(data["scheduled_time"])

                return flattened_items

        except Exception as err:
            _LOGGER.error("Error loading from storage: %s", err, exc_info=True)
            return {}

    async def async_save(self, items: Dict[str, Dict[str, Any]]) -> None:
        """Save items to storage with proper organization."""
        try:
            async with self._lock:
                # Organize items by type and status
                organized = {
                    "alarms": {
                        "active": {},
                        "scheduled": {},
                        "stopped": {}
                    },
                    "reminders": {
                        "active": {},
                        "scheduled": {},
                        "stopped": {}
                    }
                }

                for item_id, data in items.items():
                    # Create a copy for storage
                    storage_data = dict(data)
                    
                    # Convert datetime to string
                    if "scheduled_time" in storage_data:
                        if isinstance(storage_data["scheduled_time"], datetime):
                            storage_data["scheduled_time"] = storage_data["scheduled_time"].isoformat()
                    
                    # Sort into correct category
                    item_type = "alarms" if data.get("is_alarm") else "reminders"
                    status = data.get("status", "scheduled")
                    organized[item_type][status][item_id] = storage_data

                # Save alarms
                async with aiofiles.open(self.alarms_file, 'w') as f:
                    await f.write(json.dumps(organized["alarms"], cls=JSONEncoder, indent=4))

                # Save reminders
                async with aiofiles.open(self.reminders_file, 'w') as f:
                    await f.write(json.dumps(organized["reminders"], cls=JSONEncoder, indent=4))

                self._items = organized

        except Exception as err:
            _LOGGER.error("Error saving to storage: %s", err, exc_info=True)

    async def async_update_item(self, item_id: str, data: Dict[str, Any]) -> None:
        """Update a single item in storage."""
        try:
            async with self._lock:
                self._items[item_id] = data
                await self.async_save(self._items)
        except Exception as err:
            _LOGGER.error("Error updating item in storage: %s", err, exc_info=True)

    async def async_delete_item(self, item_id: str) -> None:
        """Delete an item from storage."""
        try:
            async with self._lock:
                if item_id in self._items:
                    del self._items[item_id]
                    await self.async_save(self._items)
        except Exception as err:
            _LOGGER.error("Error deleting item from storage: %s", err, exc_info=True)

    async def async_load_items(self) -> None:
        """Load items from storage and reschedule active ones."""
        try:
            self._active_items = await self.storage.async_load()
            _LOGGER.debug("Loaded items from storage: %s", self._active_items)
            
            # Process each item
            now = dt_util.now()
            for item_id, item in list(self._active_items.items()):
                if item["status"] == "active":
                    # Create stop event for active items
                    self._stop_events[item_id] = asyncio.Event()
                    
                    # Start playback for active items
                    self.hass.async_create_task(
                        self._start_playback(item_id),
                        name=f"playback_{item_id}"
                    )
                
                elif item["status"] == "scheduled":
                    # Calculate delay and schedule
                    scheduled_time = item["scheduled_time"]
                    if scheduled_time > now:
                        delay = (scheduled_time - now).total_seconds()
                        self.hass.loop.call_later(
                            delay,
                            lambda: self.hass.async_create_task(
                                self._trigger_item(item_id),
                                name=f"trigger_{item_id}"
                            )
                        )
                    else:
                        # If scheduled time is in the past, reschedule for next occurrence
                        if item.get("repeat") in ["daily", "weekdays", "weekends", "weekly"]:
                            # Handle repeated items
                            new_time = self._calculate_next_occurrence(item)
                            if new_time:
                                item["scheduled_time"] = new_time
                                delay = (new_time - now).total_seconds()
                                self.hass.loop.call_later(
                                    delay,
                                    lambda: self.hass.async_create_task(
                                        self._trigger_item(item_id),
                                        name=f"trigger_{item_id}"
                                    )
                                )
                
                # Create or update entity state
                state_data = dict(item)
                if "scheduled_time" in state_data:
                    state_data["scheduled_time"] = state_data["scheduled_time"].isoformat()
                
                self.hass.states.async_set(
                    f"{DOMAIN}.{item_id}",
                    item["status"],
                    state_data
                )

        except Exception as err:
            _LOGGER.error("Error loading items: %s", err, exc_info=True)