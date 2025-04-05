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
            _LOGGER.debug("Playing %s on target %s", sound_file, target)

            if is_satellite:
                # For satellites, use the entity_id directly
                target = f"media_player.{target}"
            else:
                # For media players, use the provided entity_id
                target = target

            # Store alarm info
            if alarm_id:
                self._active_alarms[alarm_id] = {
                    "target": target,
                    "is_alarm": is_alarm,
                    "start_time": datetime.now(),
                    "stop_event": asyncio.Event()
                }
                stop_event = self._active_alarms[alarm_id]["stop_event"]
            else:
                stop_event = self._stop_event

            # Start playback
            await self.hass.services.async_call(
                "media_player",
                "play_media",
                {
                    "entity_id": target,
                    "media_content_id": sound_file,
                    "media_content_type": "music"
                },
                blocking=True
            )
            _LOGGER.info("Started playback on %s", target)

        except Exception as err:
            _LOGGER.error("Error playing sound on %s: %s", target, err, exc_info=True)

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