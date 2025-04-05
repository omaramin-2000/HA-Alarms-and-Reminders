"""The Alarms and Reminders integration."""
import logging
import voluptuous as vol
from pathlib import Path

from homeassistant.core import HomeAssistant
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
    DEFAULT_SATELLITE,
    DEFAULT_SNOOZE_MINUTES,  # Add this import
    CONF_MEDIA_PLAYER,  # Add this import
)
from .coordinator import AlarmAndReminderCoordinator
from .media_player import MediaHandler
from .announcer import Announcer

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA = vol.Schema({
    vol.Required(ATTR_DATETIME): cv.string,
    vol.Optional(ATTR_SATELLITE, default=DEFAULT_SATELLITE): cv.string,
    vol.Optional(ATTR_MESSAGE): cv.string,
})

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Alarms and Reminders integration."""
    
    # Initialize components
    sounds_dir = Path(__file__).parent / "sounds"
    media_handler = MediaHandler(
        hass,
        str(sounds_dir / "alarms" / "birds.mp3"),
        str(sounds_dir / "reminders" / "ringtone.mp3")
    )
    announcer = Announcer(hass)
    coordinator = AlarmAndReminderCoordinator(hass, media_handler, announcer)

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ALARM,
        lambda call: coordinator.schedule_item(call, is_alarm=True),
        schema=SERVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_REMINDER,
        lambda call: coordinator.schedule_item(call, is_alarm=False),
        schema=SERVICE_SCHEMA,
    )

    # Register reminder-specific services
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_REMINDER,
        lambda call: coordinator.stop_item(
            call.data.get(ATTR_REMINDER_ID), is_alarm=False
        ),
        schema=vol.Schema({
            vol.Required(ATTR_REMINDER_ID): cv.string,
        }),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SNOOZE_REMINDER,
        lambda call: coordinator.snooze_item(
            call.data.get(ATTR_REMINDER_ID),
            call.data.get(ATTR_SNOOZE_MINUTES, DEFAULT_SNOOZE_MINUTES),
            is_alarm=False
        ),
        schema=vol.Schema({
            vol.Required(ATTR_REMINDER_ID): cv.string,
            vol.Optional(ATTR_SNOOZE_MINUTES, default=DEFAULT_SNOOZE_MINUTES): cv.positive_int,
        }),
    )

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