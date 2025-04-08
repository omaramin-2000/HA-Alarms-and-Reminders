"""Sensor platform for Alarms and Reminders."""
from datetime import datetime
import logging
from typing import Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback  
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
        self._attr_native_unit_of_measurement = "active items"
        
    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        try:
            count = sum(
                1 for item in self.coordinator._active_items.values()
                if item["is_alarm"] == self.is_alarm 
                and item["status"] in ["scheduled", "active"]
            )
            _LOGGER.debug(
                "Active %s count: %d (total items: %d)", 
                "alarms" if self.is_alarm else "reminders",
                count,
                len(self.coordinator._active_items)
            )
            return count
        except Exception as err:
            _LOGGER.error("Error calculating count: %s", err)
            return 0

    async def async_added_to_hass(self):
        """Register callbacks."""
        @callback
        def _state_changed(event):
            """Handle state changes."""
            self.async_schedule_update_ha_state(True)

        self.async_on_remove(
            self.hass.bus.async_listen(f"{DOMAIN}_state_changed", _state_changed)
        )

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        items = {}
        now = dt_util.now()
            
        # Get items from coordinator
        for item_id, item in self.coordinator._active_items.items():
            if item["is_alarm"] == self.is_alarm:
                try:
                    next_trigger = (item["scheduled_time"] - now).total_seconds()
                except Exception:
                    next_trigger = 0

                items[item_id] = {
                    "time": item["scheduled_time"].strftime("%I:%M %p"),
                    "date": item["scheduled_time"].strftime("%Y-%m-%d"),
                    "message": item["message"],
                    "repeat": item["repeat"],
                    "satellite": item["satellite"],
                    "status": item["status"],
                    "next_trigger": next_trigger
                }
        
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