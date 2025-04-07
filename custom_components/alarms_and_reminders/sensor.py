"""Sensor platform for Alarms and Reminders."""
from datetime import datetime
import logging
from typing import Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ActiveItemsSensor(coordinator, is_alarm=True),
        ActiveItemsSensor(coordinator, is_alarm=False)
    ])

class ActiveItemsSensor(SensorEntity):
    """Base class for active items sensors."""

    def __init__(self, coordinator, is_alarm: bool):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.is_alarm = is_alarm
        self._attr_unique_id = f"alarms_and_reminders_active_{'alarms' if is_alarm else 'reminders'}"
        self._attr_name = f"Active {'Alarms' if is_alarm else 'Reminders'}"
        self._attr_icon = "mdi:alarm" if is_alarm else "mdi:reminder"
        self._attr_should_poll = False

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        return len([
            entity for entity in self.hass.data[DOMAIN]["entities"]
            if entity.data["is_alarm"] == self.is_alarm and entity.state in ["scheduled", "active"]
        ])

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        items = {}
        now = dt_util.now()
        
        for item_id, item in self.coordinator._active_items.items():
            if item["is_alarm"] == self.is_alarm:
                items[item_id] = {
                    "time": item["scheduled_time"].strftime("%I:%M %p"),
                    "date": item["scheduled_time"].strftime("%Y-%m-%d"),
                    "message": item["message"],
                    "repeat": item["repeat"],
                    "target": item["target"],
                    "status": item["status"],
                    "next_trigger": (item["scheduled_time"] - now).total_seconds()
                }
        
        _LOGGER.debug("Sensor attributes for %s: %s", "alarms" if self.is_alarm else "reminders", items)
        return {
            "items": items,
            "last_updated": now.isoformat()
        }

    async def async_update(self) -> None:
        """Update the sensor."""
        self.async_write_ha_state()
