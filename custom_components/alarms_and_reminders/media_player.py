"""Handle media playback for alarms and reminders."""
import asyncio
import logging
from datetime import datetime, timedelta
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
        self._active_alarms = {}  # Store active alarms/reminders
        self._stop_event = asyncio.Event()

    async def play_sound(self, target: str, is_alarm: bool, is_satellite: bool = True, alarm_id: str = None) -> None:
        """Play the appropriate sound file."""
        try:
            sound_file = self.alarm_sound if is_alarm else self.reminder_sound
            _LOGGER.debug("Playing %s on target %s (is_satellite: %s)", sound_file, target, is_satellite)

            # Determine the full entity_id
            if is_satellite:
                entity_id = f"assist_satellite.{target}"
            else:
                entity_id = target  # media_player entity_id is already complete

            _LOGGER.info("Playing on entity: %s", entity_id)

            # Start playback
            await self.hass.services.async_call(
                "media_player",
                "play_media",
                {
                    "entity_id": entity_id,
                    "media_content_id": sound_file,
                    "media_content_type": "music",
                },
                blocking=True
            )
            
            # Log success
            _LOGGER.info("Successfully started playback on %s", entity_id)

        except Exception as err:
            _LOGGER.error("Error playing sound on %s: %s", target, err, exc_info=True)
            raise

    async def stop_alarm(self, alarm_id: str) -> None:
        """Stop a specific alarm."""
        if alarm_id in self._active_alarms:
            self._active_alarms[alarm_id]["stop_event"].set()
            del self._active_alarms[alarm_id]

    async def snooze_alarm(self, alarm_id: str, snooze_minutes: int = 5) -> None:
        """Snooze a specific alarm."""
        if alarm_id in self._active_alarms:
            # Stop current ringing
            await self.stop_alarm(alarm_id)
            
            # Schedule to ring again after snooze period
            alarm_info = self._active_alarms[alarm_id]
            snooze_delay = timedelta(minutes=snooze_minutes)
            
            await asyncio.sleep(snooze_delay.total_seconds())
            await self.play_sound(
                alarm_info["target"],
                alarm_info["is_alarm"],
                is_satellite="satellite" in alarm_info["target"],
                alarm_id=alarm_id
            )
