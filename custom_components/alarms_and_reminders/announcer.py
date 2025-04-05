"""Handle TTS announcements for alarms and reminders."""
import logging
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class Announcer:
    """Handles TTS announcements for alarms and reminders."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize announcer."""
        self.hass = hass

    async def make_announcement(self, satellite: str, time_str: str, 
                              message: str, is_alarm: bool) -> None:
        """Make the TTS announcement."""
        if is_alarm:
            announcement = f"It's {time_str}. {message}" if message else f"It's {time_str}."
        else:
            announcement = f"Reminder at {time_str}: {message}" if message else f"Reminder notification at {time_str}"

        await self.hass.services.async_call(
            "assist_satellite", 
            "announce",
            {
                "satellite": satellite,
                "message": announcement,
            }
        )
        
        _LOGGER.info("Announced on satellite '%s': %s", satellite, announcement)