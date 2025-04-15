"""The Alarms and Reminders integration."""
from __future__ import annotations

import logging
import voluptuous as vol
from pathlib import Path
from typing import Union
from datetime import time, datetime
import importlib

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import ATTR_NAME  # Use HA's built-in ATTR_NAME

from .const import (
    DOMAIN,
    SERVICE_SET_ALARM,
    SERVICE_SET_REMINDER,
    SERVICE_STOP_ALARM,    
    SERVICE_SNOOZE_ALARM,  
    SERVICE_STOP_REMINDER,
    SERVICE_SNOOZE_REMINDER,
    ATTR_DATETIME,
    ATTR_SATELLITE,
    ATTR_MESSAGE,
    ATTR_ALARM_ID,        
    ATTR_REMINDER_ID,
    ATTR_SNOOZE_MINUTES,
    ATTR_MEDIA_PLAYER,
    DEFAULT_SATELLITE,
    DEFAULT_SNOOZE_MINUTES,
    CONF_MEDIA_PLAYER,
)  

from .coordinator import AlarmAndReminderCoordinator
from .media_player import MediaHandler
from .announcer import Announcer
from .intents import async_setup_intents
from .sensor import async_setup_entry as async_setup_sensor_entry

__all__ = ["AlarmAndReminderCoordinator"]

_LOGGER = logging.getLogger(__name__)

REPEAT_OPTIONS = [
    "once",
    "daily",
    "weekdays",
    "weekends",
    "weekly",
    "custom"
]

async def _get_satellites(hass: HomeAssistant) -> list:
    """Get list of configured assist satellites."""
    try:
        satellites = [
            entity_id.split('.')[1]  # Extract satellite ID
            for entity_id in hass.states.async_entity_ids("assist_satellite")
        ]
        
        if not satellites:
            _LOGGER.warning("No satellites found, functionality may be limited")
            satellites = ["default_satellite"]  # Add a default satellite for testing
        
        _LOGGER.debug("Available satellites: %s", satellites)
        return satellites
    except Exception as err:
        _LOGGER.error("Error getting satellites list: %s", err, exc_info=True)
        return []

PLATFORMS = ["sensor"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Alarms and Reminders integration."""
    try:
        # Initialize data structure
        hass.data.setdefault(DOMAIN, {})

        # Initialize components directly without async imports
        sounds_dir = Path(__file__).parent / "sounds"
        media_handler = MediaHandler(
            hass,
            str(sounds_dir / "alarms" / "birds.mp3"),
            str(sounds_dir / "reminders" / "ringtone.mp3")
        )
        announcer = Announcer(hass)
        coordinator = AlarmAndReminderCoordinator(
            hass, media_handler, announcer
        )

        # Initialize the DOMAIN data structure
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {"entities": []}  # Initialize the entities list

        # Get available satellites
        satellites = await _get_satellites(hass)
        
        # Dynamic schema based on available satellites and media players
        ALARM_SERVICE_SCHEMA = vol.Schema({
            vol.Required("time"): cv.time,  # Make time required
            vol.Optional("date"): cv.date,
            vol.Optional(ATTR_NAME): str,  # Optional name for alarms
            vol.Optional(ATTR_MESSAGE): cv.string,
            vol.Optional(ATTR_SATELLITE): cv.entity_id,
            vol.Optional(ATTR_MEDIA_PLAYER): vol.All(cv.ensure_list, [cv.entity_id]),
            vol.Optional("repeat", default="once"): vol.In(REPEAT_OPTIONS),
            vol.Optional("repeat_days"): vol.All(
                cv.ensure_list,
                [vol.In(["mon", "tue", "wed", "thu", "fri", "sat", "sun"])]
            ),
        })

        REMINDER_SERVICE_SCHEMA = vol.Schema({
            vol.Required("time"): cv.time,  # Make time required
            vol.Required(ATTR_NAME): str,  # Required name for reminders
            vol.Optional("date"): cv.date,
            vol.Optional(ATTR_MESSAGE): cv.string,
            vol.Optional(ATTR_SATELLITE): cv.entity_id,
            vol.Optional(ATTR_MEDIA_PLAYER): vol.All(cv.ensure_list, [cv.entity_id]),
            vol.Optional("repeat", default="once"): vol.In(REPEAT_OPTIONS),
            vol.Optional("repeat_days"): vol.All(
                cv.ensure_list,
                [vol.In(["mon", "tue", "wed", "thu", "fri", "sat", "sun"])]
            ),
        })

        # Store coordinator for future access
        hass.data[DOMAIN]["coordinator"] = coordinator

        def validate_target(call: ServiceCall) -> dict:
            """Validate that either satellite or media_player is provided."""
            satellite = call.data.get(ATTR_SATELLITE)
            media_players = call.data.get(ATTR_MEDIA_PLAYER, [])

            if not satellite and not media_players:
                raise vol.Invalid("No valid target found. Configure a satellite or specify one or more media players.")

            _LOGGER.debug("Validated target: satellite=%s, media_players=%s", satellite, media_players)
            return {"satellite": satellite, "media_players": media_players}

        async def async_schedule_alarm(call: ServiceCall):
            """Handle the alarm service call."""
            target = validate_target(call)
            await coordinator.schedule_item(call, is_alarm=True, target=target)

        async def async_schedule_reminder(call: ServiceCall):
            """Handle the reminder service call."""
            target = validate_target(call)
            await coordinator.schedule_item(call, is_alarm=False, target=target)

        # Register services with updated schema
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_ALARM,
            async_schedule_alarm,
            schema=ALARM_SERVICE_SCHEMA,
        )

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_REMINDER,
            async_schedule_reminder,
            schema=REMINDER_SERVICE_SCHEMA,
        )

        # Register reminder-specific services
        async def async_stop_reminder(call: ServiceCall):
            """Handle stop reminder service call."""
            try:
                reminder_id = call.data.get(ATTR_REMINDER_ID)
                coordinator = None
                
                # First try to get coordinator from root level
                if "coordinator" in hass.data[DOMAIN]:
                    coordinator = hass.data[DOMAIN]["coordinator"]
                else:
                    # Try to get from first config entry
                    for entry_id, data in hass.data[DOMAIN].items():
                        if isinstance(data, dict) and "coordinator" in data:
                            coordinator = data["coordinator"]
                            break
                
                if coordinator:
                    _LOGGER.debug("Found coordinator. Active items: %s", coordinator._active_items)
                    await coordinator.stop_item(reminder_id, is_alarm=False)
                else:
                    _LOGGER.error("No coordinator found in hass.data[DOMAIN]: %s", hass.data[DOMAIN])
                    
            except Exception as err:
                _LOGGER.error("Error stopping reminder: %s", err, exc_info=True)

        hass.services.async_register(
            DOMAIN,
            SERVICE_STOP_REMINDER,
            async_stop_reminder,
            schema=vol.Schema({
                vol.Required(ATTR_REMINDER_ID): cv.entity_id,  # Changed from cv.string to cv.entity_id
            }),
        )

        async def async_snooze_reminder(call: ServiceCall):
            """Handle snooze reminder service call."""
            await coordinator.snooze_item(
                call.data.get(ATTR_REMINDER_ID),
                call.data.get(ATTR_SNOOZE_MINUTES, DEFAULT_SNOOZE_MINUTES),
                is_alarm=False
            )

        hass.services.async_register(
            DOMAIN,
            SERVICE_SNOOZE_REMINDER,
            async_snooze_reminder,  # Changed from lambda
            schema=vol.Schema({
                vol.Required(ATTR_REMINDER_ID): cv.string,
                vol.Optional(ATTR_SNOOZE_MINUTES, default=DEFAULT_SNOOZE_MINUTES): cv.positive_int,
            }),
        )

        async def async_stop_alarm(call: ServiceCall):
            """Handle stop alarm service call."""
            alarm_id = call.data.get("alarm_id")
            await coordinator.stop_item(alarm_id, is_alarm=True)

        async def async_snooze_alarm(call: ServiceCall):
            """Handle snooze alarm service call."""
            alarm_id = call.data.get("alarm_id")
            minutes = call.data.get("minutes", DEFAULT_SNOOZE_MINUTES)
            await coordinator.snooze_item(alarm_id, minutes, is_alarm=True)

        # Register alarm control services
        hass.services.async_register(
            DOMAIN,
            "stop_alarm",
            async_stop_alarm,
            schema=vol.Schema({
                vol.Required("alarm_id"): cv.string,
            }),
        )

        hass.services.async_register(
            DOMAIN,
            "snooze_alarm",
            async_snooze_alarm,
            schema=vol.Schema({
                vol.Required("alarm_id"): cv.string,
                vol.Optional("minutes", default=DEFAULT_SNOOZE_MINUTES): cv.positive_int,
            }),
        )

        # Register alarm-specific services
        async def async_stop_alarm(call: ServiceCall):
            """Handle stop alarm service call."""
            try:
                alarm_id = call.data.get(ATTR_ALARM_ID)
                coordinator = None
                
                # First try to get coordinator from root level
                if "coordinator" in hass.data[DOMAIN]:
                    coordinator = hass.data[DOMAIN]["coordinator"]
                else:
                    # Try to get from first config entry
                    for entry_id, data in hass.data[DOMAIN].items():
                        if isinstance(data, dict) and "coordinator" in data:
                            coordinator = data["coordinator"]
                            break
                
                if coordinator:
                    _LOGGER.debug("Found coordinator. Active items: %s", coordinator._active_items)
                    await coordinator.stop_item(alarm_id, is_alarm=True)
                else:
                    _LOGGER.error("No coordinator found in hass.data[DOMAIN]: %s", hass.data[DOMAIN])
                    
            except Exception as err:
                _LOGGER.error("Error stopping alarm: %s", err, exc_info=True)

        hass.services.async_register(
            DOMAIN,
            SERVICE_STOP_ALARM,
            async_stop_alarm,
            schema=vol.Schema({
                vol.Required(ATTR_ALARM_ID): cv.entity_id,  # Changed from cv.string to cv.entity_id
            }),
        )

        # Register reminder-specific services
        async def async_stop_reminder(call: ServiceCall):
            """Handle stop reminder service call."""
            try:
                reminder_id = call.data.get(ATTR_REMINDER_ID)
                coordinator = None
                
                # First try to get coordinator from root level
                if "coordinator" in hass.data[DOMAIN]:
                    coordinator = hass.data[DOMAIN]["coordinator"]
                else:
                    # Try to get from first config entry
                    for entry_id, data in hass.data[DOMAIN].items():
                        if isinstance(data, dict) and "coordinator" in data:
                            coordinator = data["coordinator"]
                            break
                
                if coordinator:
                    _LOGGER.debug("Found coordinator. Active items: %s", coordinator._active_items)
                    await coordinator.stop_item(reminder_id, is_alarm=False)
                else:
                    _LOGGER.error("No coordinator found in hass.data[DOMAIN]: %s", hass.data[DOMAIN])
                    
            except Exception as err:
                _LOGGER.error("Error stopping reminder: %s", err, exc_info=True)

        hass.services.async_register(
            DOMAIN,
            SERVICE_STOP_REMINDER,
            async_stop_reminder,
            schema=vol.Schema({
                vol.Required(ATTR_REMINDER_ID): cv.string,
            }),
        )

        # Register new services
        hass.services.async_register(
            DOMAIN,
            "stop_all_alarms",
            async_stop_all_alarms,
            schema=vol.Schema({}),
        )

        hass.services.async_register(
            DOMAIN,
            "stop_all_reminders",
            async_stop_all_reminders,
            schema=vol.Schema({}),
        )

        hass.services.async_register(
            DOMAIN,
            "stop_all",
            async_stop_all,
            schema=vol.Schema({}),
        )

        # Set up intents
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
            await async_setup_intents(hass)  # Only setup intents once

        return True

    except Exception as err:
        _LOGGER.error("Error setting up integration: %s", err, exc_info=True)
        return False

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    try:
        # Initialize data structure if not exists
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        # Initialize components
        sounds_dir = Path(__file__).parent / "sounds"
        media_handler = MediaHandler(
            hass,
            str(sounds_dir / "alarms" / "birds.mp3"),
            str(sounds_dir / "reminders" / "ringtone.mp3")
        )
        announcer = Announcer(hass)
        coordinator = AlarmAndReminderCoordinator(
            hass, media_handler, announcer
        )

        # Store coordinator and initialize entities list
        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
            "entities": []
        }

        # Forward setup to platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        # Set up update listener
        entry.async_on_unload(entry.add_update_listener(update_listener))
        
        return True

    except Exception as err:
        _LOGGER.error("Error setting up config entry: %s", err, exc_info=True)
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_stop_all_alarms(call: ServiceCall):
    """Handle stop all alarms service call."""
    try:
        coordinator = None
        for entry_id, data in hass.data[DOMAIN].items():
            if isinstance(data, dict) and "coordinator" in data:
                coordinator = data["coordinator"]
                break
        
        if coordinator:
            await coordinator.stop_all_items(is_alarm=True)
    except Exception as err:
        _LOGGER.error("Error stopping all alarms: %s", err)

async def async_stop_all_reminders(call: ServiceCall):
    """Handle stop all reminders service call."""
    try:
        coordinator = None
        for entry_id, data in hass.data[DOMAIN].items():
            if isinstance(data, dict) and "coordinator" in data:
                coordinator = data["coordinator"]
                break
        
        if coordinator:
            await coordinator.stop_all_items(is_alarm=False)
    except Exception as err:
        _LOGGER.error("Error stopping all reminders: %s", err)

async def async_stop_all(call: ServiceCall):
    """Handle stop all service call."""
    try:
        coordinator = None
        for entry_id, data in hass.data[DOMAIN].items():
            if isinstance(data, dict) and "coordinator" in data:
                coordinator = data["coordinator"]
                break
        
        if coordinator:
            await coordinator.stop_all_items()
    except Exception as err:
        _LOGGER.error("Error stopping all items: %s", err)