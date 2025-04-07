"""Sensor platform for Alarms and Reminders."""
from datetime import datetime
import logging
from typing import Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
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
    
    # Create and add sensor entities
    entities = [
        ActiveItemsSensor(coordinator, is_alarm=True),
        ActiveItemsSensor(coordinator, is_alarm=False)
    ]
    
    async_add_entities(entities)

    # Store the async_add_entities callback for future dynamic entity creation
    coordinator.async_add_entities = async_add_entities

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
        entities = self.hass.data[DOMAIN].get("entities", [])
        return len([
            entity for entity in entities
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

    async def schedule_item(self, call: ServiceCall, is_alarm: bool, target: dict) -> None:
        """Schedule an alarm or reminder."""
        try:
            _LOGGER.debug("Scheduling %s with data: %s", "alarm" if is_alarm else "reminder", call.data)
            
            # ...existing code...

            # Create entity for the alarm/reminder
            entity = AlarmReminderEntity(self.hass, item_id, self._active_items[item_id])
            self.hass.data[DOMAIN]["entities"].append(entity)

            if self.async_add_entities:
                self.async_add_entities([entity])  # Use the callback to add the entity

            _LOGGER.info(
                "Scheduled %s '%s' for %s (in %d seconds) on satellite '%s' and media players %s",
                "alarm" if is_alarm else "reminder",
                item_id,
                scheduled_time,
                delay,
                target.get("satellite"),
                target.get("media_players")
            )

            # ...existing code...

        except Exception as err:
            _LOGGER.error("Error scheduling: %s", err, exc_info=True)
            raise
