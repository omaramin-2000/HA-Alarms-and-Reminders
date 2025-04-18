"""Handle media playback for alarms and reminders."""
import asyncio
import logging
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class MediaHandler:
    """Handles playing sounds and TTS on media players."""
    
    def __init__(self, hass: HomeAssistant, alarm_sound: str, reminder_sound: str):
        """Initialize media handler."""
        self.hass = hass
        self.alarm_sound = alarm_sound
        self.reminder_sound = reminder_sound
        self._active_alarms = {}  # Store active alarms/reminders

    async def play_on_media_player(self, media_player: str, message: str, is_alarm: bool) -> None:
        """Play TTS and sound on media player."""
        try:
            # Play TTS announcement first
            await self.hass.services.async_call(
                "tts",
                "speak",
                {
                    "entity_id": media_player,
                    "message": message,
                    "language": "en"
                },
                blocking=True
            )

            # Wait for TTS to finish
            await asyncio.sleep(1)

            # Play sound file
            sound_file = self.alarm_sound if is_alarm else self.reminder_sound
            await self.hass.services.async_call(
                "media_player",
                "play_media",
                {
                    "entity_id": media_player,
                    "media_content_id": sound_file,
                    "media_content_type": "music"
                },
                blocking=True
            )

        except Exception as err:
            _LOGGER.error("Error playing on media player %s: %s", media_player, err)

    async def play_sound(self, satellite: str, media_players: list, is_alarm: bool, message: str) -> None:
        """Play the appropriate sound file."""
        try:
            if media_players:
                for media_player in media_players:
                    await self.play_on_media_player(media_player, message, is_alarm)

        except Exception as err:
            _LOGGER.error("Error playing sound: %s", err, exc_info=True)
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