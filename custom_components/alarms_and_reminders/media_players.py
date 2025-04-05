"""Handle media playback for alarms and reminders."""
import asyncio
import logging
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class MediaHandler:
    """Handles playing sounds for alarms and reminders."""
    
    def __init__(self, hass: HomeAssistant, alarm_sound: str, reminder_sound: str, media_player: str = None):
        """Initialize media handler."""
        self.hass = hass
        self.alarm_sound = alarm_sound
        self.reminder_sound = reminder_sound
        self.media_player = media_player

    async def play_sound(self, target: str, is_alarm: bool, is_satellite: bool = True) -> None:
        """Play the appropriate sound file on either satellite or media player."""
        sound_file = self.alarm_sound if is_alarm else self.reminder_sound
        
        try:
            if is_satellite:
                # Use satellite's media player
                satellite_config = await self.hass.services.async_call(
                    "assist_satellite",
                    "get_config",
                    {"satellite": target}
                )
                
                if satellite_config and "media_player" in satellite_config:
                    target = satellite_config["media_player"]
                else:
                    _LOGGER.error("No media player configured for satellite %s", target)
                    return
            else:
                # Use configured media player from dashboard
                if not self.media_player:
                    _LOGGER.error("No media player configured in integration settings")
                    return
                target = self.media_player

            await self.hass.services.async_call(
                "media_player",
                "play_media",
                {
                    "entity_id": target,
                    "media_content_id": sound_file,
                    "media_content_type": "music"
                }
            )
            
            # Wait for sound to finish
            await asyncio.sleep(3)  # Adjust based on sound length
            
        except Exception as err:
            _LOGGER.error("Error playing sound on %s: %s", target, err)