"""Sensor platform for Alarms and Reminders."""
from datetime import datetime
import logging
from typing import Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
        ActiveAlarmsSensor(coordinator),
        ActiveRemindersSensor(coordinator)
    ])

class ActiveAlarmsSensor(SensorEntity):
    """Sensor showing active alarms."""

    _attr_has_entity_name = True
    _attr_name = "Active Alarms"
    _attr_icon = "mdi:alarm"

    def __init__(self, coordinator):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_active_alarms"

    @property
    def state(self) -> int:
        """Return the number of active alarms."""
        return len([item for item_id, item in self.coordinator._active_items.items() 
                   if item["is_alarm"]])

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        alarms = {}
        for item_id, item in self.coordinator._active_items.items():
            if item["is_alarm"]:
                alarms[item_id] = {
                    "time": item["scheduled_time"].strftime("%I:%M %p"),
                    "message": item["message"],
                    "repeat": item["repeat"],
                    "target": item["target"]
                }
        return {
            "alarms": alarms
        }

class ActiveRemindersSensor(SensorEntity):
    """Sensor showing active reminders."""

    _attr_has_entity_name = True
    _attr_name = "Active Reminders"
    _attr_icon = "mdi:reminder"

    def __init__(self, coordinator):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_active_reminders"

    @property
    def state(self) -> int:
        """Return the number of active reminders."""
        return len([item for item_id, item in self.coordinator._active_items.items() 
                   if not item["is_alarm"]])

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        reminders = {}
        for item_id, item in self.coordinator._active_items.items():
            if not item["is_alarm"]:
                reminders[item_id] = {
                    "time": item["scheduled_time"].strftime("%I:%M %p"),
                    "message": item["message"],
                    "repeat": item["repeat"],
                    "target": item["target"]
                }
        return {
            "reminders": reminders
        }