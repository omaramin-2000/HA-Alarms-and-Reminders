# custom_components/alarms_and_reminders/__init__.py

import logging
import datetime
from dateutil import parser
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "assist_alarm"
SERVICE_SET_ALARM = "set_alarm"

ATTR_DATETIME = "datetime"      # A string containing the alarm time
ATTR_SATELLITE = "satellite"    # The satellite ID to announce the alarm on
ATTR_MESSAGE = "message"        # The announcement message (optional)

SERVICE_SET_ALARM_SCHEMA = vol.Schema({
    vol.Required(ATTR_DATETIME): cv.string,
    vol.Optional(ATTR_SATELLITE, default="default_satellite"): cv.string,
    vol.Optional(ATTR_MESSAGE, default="Alarm Time!"): cv.string,
})


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Assist Alarm integration."""

    async def handle_set_alarm(call: ServiceCall) -> None:
        datetime_str = call.data.get(ATTR_DATETIME)
        satellite = call.data.get(ATTR_SATELLITE)
        message = call.data.get(ATTR_MESSAGE)

        # Attempt to parse the datetime string (this can be built to also add logic for "today", "tomorrow", etc.)
        try:
            alarm_time = parser.parse(datetime_str, fuzzy=True)
        except Exception as err:
            _LOGGER.error("Error parsing datetime '%s': %s", datetime_str, err)
            return

        now = datetime.datetime.now(alarm_time.tzinfo) if alarm_time.tzinfo else datetime.datetime.now()
        delay = (alarm_time - now).total_seconds()
        if delay < 0:
            _LOGGER.warning("Alarm time is in the past. Ignoring the request.")
            return

        _LOGGER.info("Setting alarm for %s (in %s seconds) on satellite '%s'", alarm_time, delay, satellite)

        async def alarm_action(now_time):
            """Action to execute when the alarm triggers."""
            data = {
                "satellite": satellite,
                "message": message,
            }
            await hass.services.async_call("assist_satellite", "announce", data)
            _LOGGER.info("Alarm triggered at %s. Announced on satellite '%s'", now_time, satellite)

        # Schedule the alarm action using hass.loop.call_later.
        hass.loop.call_later(delay, lambda: hass.async_create_task(alarm_action(datetime.datetime.now())))

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ALARM,
        handle_set_alarm,
        schema=SERVICE_SET_ALARM_SCHEMA,
    )

    return True
