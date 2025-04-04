import logging
import datetime
import asyncio
from dateutil import parser
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import CONF_NAME
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

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA = vol.Schema({
    vol.Required(ATTR_DATETIME): cv.string,
    vol.Optional(ATTR_SATELLITE, default=DEFAULT_SATELLITE): cv.string,
    vol.Optional(ATTR_MESSAGE): cv.string,
})

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Alarms and Reminders integration."""

    async def handle_schedule(call: ServiceCall, is_alarm: bool) -> None:
        datetime_str = call.data.get(ATTR_DATETIME)
        satellite = call.data.get(ATTR_SATELLITE)
        message = call.data.get(ATTR_MESSAGE)

        try:
            scheduled_time = parser.parse(datetime_str, fuzzy=True)
        except Exception as err:
            _LOGGER.error("Error parsing datetime '%s': %s", datetime_str, err)
            return

        now = datetime.datetime.now(scheduled_time.tzinfo) if scheduled_time.tzinfo else datetime.datetime.now()
        delay = (scheduled_time - now).total_seconds()
        
        if delay < 0:
            _LOGGER.warning("Scheduled time is in the past. Ignoring the request.")
            return

        item_type = "alarm" if is_alarm else "reminder"
        _LOGGER.info(f"Setting {item_type} for %s (in %s seconds) on satellite '%s'", scheduled_time, delay, satellite)

        async def announcement_action(now_time):
            """Action to execute when the alarm/reminder triggers."""
            time_str = scheduled_time.strftime("%I:%M %p")
            
            if is_alarm:
                # Play alarm sound first
                await hass.services.async_call(
                    "media_player",
                    "play_media",
                    {
                        "entity_id": satellite,
                        "media_content_id": "/custom_components/alarms_and_reminders/sounds/alarms/birds.mp3",
                        "media_content_type": "music"
                    }
                )
                
                # Wait for sound to finish (adjust timing as needed)
                await asyncio.sleep(3)
                
                # Then do the TTS announcement
                if message:
                    announcement = f"It's {time_str}. {message}"
                else:
                    announcement = f"It's {time_str}."
            else:
                if message:
                    announcement = f"Reminder at {time_str}: {message}"
                else:
                    announcement = f"Reminder notification at {time_str}"

            # Make the announcement
            data = {
                "satellite": satellite,
                "message": announcement,
            }
            
            await hass.services.async_call("assist_satellite", "announce", data)
            _LOGGER.info(f"{item_type.capitalize()} triggered at %s. Announced on satellite '%s'", now_time, satellite)

        # Schedule the action
        hass.loop.call_later(delay, lambda: hass.async_create_task(announcement_action(datetime.datetime.now())))

    # Register both services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ALARM,
        lambda call: handle_schedule(call, is_alarm=True),
        schema=SERVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_REMINDER,
        lambda call: handle_schedule(call, is_alarm=False),
        schema=SERVICE_SCHEMA,
    )

    return True