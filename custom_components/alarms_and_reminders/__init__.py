"""The Alarms and Reminders integration."""
import logging
import voluptuous as vol
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_SET_ALARM,
    SERVICE_SET_REMINDER,
    ATTR_DATETIME,
    ATTR_SATELLITE,
    ATTR_MESSAGE,
    DEFAULT_SATELLITE,
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

    return True