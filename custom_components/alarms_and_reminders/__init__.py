"""The Alarms and Reminders integration."""
import logging
import voluptuous as vol
from pathlib import Path
from typing import Union
from datetime import time, datetime

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_SET_ALARM,
    SERVICE_SET_REMINDER,
    SERVICE_STOP_REMINDER,
    SERVICE_SNOOZE_REMINDER,
    ATTR_DATETIME,
    ATTR_SATELLITE,
    ATTR_MESSAGE,
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
        
        return satellites
    except Exception as err:
        _LOGGER.error("Error getting satellites list: %s", err)
        return []

PLATFORMS = ["sensor"]

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Alarms and Reminders integration."""
    
    # Get available satellites
    satellites = await _get_satellites(hass)
    
    # Dynamic schema based on available satellites and media players
    SERVICE_SCHEMA = vol.Schema({
        vol.Exclusive(ATTR_SATELLITE, 'target'): vol.In(await _get_satellites(hass)),
        vol.Exclusive(ATTR_MEDIA_PLAYER, 'target'): cv.entity_id,
        vol.Required("time"): cv.time,
        vol.Optional("date"): cv.date,
        vol.Optional(ATTR_MESSAGE): cv.string,
        vol.Optional("repeat", default="once"): vol.In(REPEAT_OPTIONS),
        vol.Optional("repeat_days"): vol.All(
            cv.ensure_list,
            [vol.In(["mon", "tue", "wed", "thu", "fri", "sat", "sun"])]
        ),
    })

    # Initialize components
    sounds_dir = Path(__file__).parent / "sounds"
    media_handler = MediaHandler(
        hass,
        str(sounds_dir / "alarms" / "birds.mp3"),
        str(sounds_dir / "reminders" / "ringtone.mp3")
    )
    announcer = Announcer(hass)
    coordinator = AlarmAndReminderCoordinator(hass, media_handler, announcer)

    def validate_target(call: ServiceCall) -> str:
        """Validate that either satellite or media_player is provided."""
        satellite = call.data.get(ATTR_SATELLITE)
        media_player = call.data.get(ATTR_MEDIA_PLAYER)
        
        if satellite:
            _LOGGER.debug("Satellite selected: %s", satellite)
            return satellite.split('.')[1]  # Extract satellite ID
        if media_player:
            _LOGGER.debug("Media player selected: %s", media_player)
            return media_player
            
        # If neither provided, try to use first available satellite
        available_satellites = hass.states.async_entity_ids("assist_satellite")
        if available_satellites:
            _LOGGER.debug("Defaulting to first available satellite: %s", available_satellites[0])
            return available_satellites[0].split('.')[1]
            
        raise vol.Invalid("No valid target found. Configure a satellite or specify a media player.")

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
        async_schedule_alarm,  # Changed from lambda
        schema=SERVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_REMINDER,
        async_schedule_reminder,  # Changed from lambda
        schema=SERVICE_SCHEMA,
    )

    # Register reminder-specific services
    async def async_stop_reminder(call: ServiceCall):
        """Handle stop reminder service call."""
        await coordinator.stop_item(call.data.get(ATTR_REMINDER_ID), is_alarm=False)

    async def async_snooze_reminder(call: ServiceCall):
        """Handle snooze reminder service call."""
        await coordinator.snooze_item(
            call.data.get(ATTR_REMINDER_ID),
            call.data.get(ATTR_SNOOZE_MINUTES, DEFAULT_SNOOZE_MINUTES),
            is_alarm=False
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_REMINDER,
        async_stop_reminder,  # Changed from lambda
        schema=vol.Schema({
            vol.Required(ATTR_REMINDER_ID): cv.string,
        }),
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

    # Set up intents
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
        await async_setup_intents(hass)  # Only setup intents once

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alarms and Reminders from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Initialize components
    sounds_dir = Path(__file__).parent / "sounds"
    media_handler = MediaHandler(
        hass,
        str(sounds_dir / "alarms" / "birds.mp3"),
        str(sounds_dir / "reminders" / "ringtone.mp3"),
        entry.options.get(CONF_MEDIA_PLAYER)  # Get media player from config
    )
    announcer = Announcer(hass)
    coordinator = AlarmAndReminderCoordinator(hass, media_handler, announcer)

    # Store coordinator for future access
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up services
    await async_setup(hass, entry.data)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, []):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)
