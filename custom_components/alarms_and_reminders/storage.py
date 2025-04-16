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
        self._items: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def async_load(self) -> Dict[str, Dict[str, Any]]:
        """Load items from storage."""
        try:
            async with self._lock:
                items = {}
                
                # Load alarms
                if self.alarms_file.exists():
                    async with aiofiles.open(self.alarms_file, 'r') as f:
                        content = await f.read()
                        alarms_data = json.loads(content)
                        for item_id, data in alarms_data.items():
                            if "scheduled_time" in data:
                                data["scheduled_time"] = dt_util.parse_datetime(data["scheduled_time"])
                            items[item_id] = data

                # Load reminders
                if self.reminders_file.exists():
                    async with aiofiles.open(self.reminders_file, 'r') as f:
                        content = await f.read()
                        reminders_data = json.loads(content)
                        for item_id, data in reminders_data.items():
                            if "scheduled_time" in data:
                                data["scheduled_time"] = dt_util.parse_datetime(data["scheduled_time"])
                            items[item_id] = data

                self._items = items
                return items

        except Exception as err:
            _LOGGER.error("Error loading from storage: %s", err, exc_info=True)
            return {}

    async def async_save(self, items: Dict[str, Dict[str, Any]]) -> None:
        """Save items to storage."""
        try:
            async with self._lock:
                # Separate alarms and reminders
                alarms = {}
                reminders = {}
                
                for item_id, data in items.items():
                    # Create a copy of the data for storage
                    storage_data = dict(data)
                    
                    # Convert datetime to string for storage
                    if "scheduled_time" in storage_data:
                        if isinstance(storage_data["scheduled_time"], datetime):
                            storage_data["scheduled_time"] = storage_data["scheduled_time"].isoformat()
                    
                    if data.get("is_alarm"):
                        alarms[item_id] = storage_data
                    else:
                        reminders[item_id] = storage_data

                # Save alarms
                async with aiofiles.open(self.alarms_file, 'w') as f:
                    await f.write(json.dumps(alarms, cls=JSONEncoder, indent=4))

                # Save reminders
                async with aiofiles.open(self.reminders_file, 'w') as f:
                    await f.write(json.dumps(reminders, cls=JSONEncoder, indent=4))

                self._items = items

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