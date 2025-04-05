"""Coordinator for scheduling alarms and reminders."""
import datetime
from dateutil import parser
import logging
from homeassistant.core import HomeAssistant, ServiceCall

_LOGGER = logging.getLogger(__name__)

class AlarmAndReminderCoordinator:
    """Coordinates scheduling of alarms and reminders."""
    
    def __init__(self, hass: HomeAssistant, media_handler, announcer):
        """Initialize coordinator."""
        self.hass = hass
        self.media_handler = media_handler
        self.announcer = announcer

    async def schedule_item(self, call: ServiceCall, is_alarm: bool) -> None:
        """Schedule an alarm or reminder."""
        datetime_str = call.data.get("datetime")
        satellite = call.data.get("satellite")
        message = call.data.get("message")

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
        _LOGGER.info(f"Setting {item_type} for %s (in %s seconds) on satellite '%s'", 
                    scheduled_time, delay, satellite)

        # Schedule the action
        self.hass.loop.call_later(
            delay, 
            lambda: self.hass.async_create_task(
                self._trigger_item(scheduled_time, satellite, message, is_alarm)
            )
        )

    async def _trigger_item(self, scheduled_time: datetime, satellite: str, 
                           message: str, is_alarm: bool) -> None:
        """Trigger the scheduled item."""
        time_str = scheduled_time.strftime("%I:%M %p")
        
        # Play sound
        await self.media_handler.play_sound(satellite, is_alarm)
        
        # Make announcement
        await self.announcer.make_announcement(satellite, time_str, message, is_alarm)