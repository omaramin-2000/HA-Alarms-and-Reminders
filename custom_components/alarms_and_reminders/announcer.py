"""Handle announcements and sounds on satellites."""
import logging
import asyncio
from datetime import datetime
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util 

_LOGGER = logging.getLogger(__name__)

class Announcer:
    """Handles announcements and sounds on satellites."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize announcer."""
        self.hass = hass
        self._stop_event = None

    async def announce_on_satellite(self, satellite: str, message: str, sound_file: str, 
                                    stop_event=None, name: str = None, is_alarm: bool = False) -> None:
        """Make announcement and play sound on satellite."""
        try:
            # Store stop event
            self._stop_event = stop_event

            # Ensure proper entity_id format
            satellite_entity_id = (
                satellite if satellite.startswith("assist_satellite.") 
                else f"assist_satellite.{satellite}"
            )

            while True:
                if self._stop_event and self._stop_event.is_set():
                    _LOGGER.debug("Announcement loop stopped")
                    break

                try:
                    # Format announcement based on type and name
                    now = dt_util.now()  # Get local time from HA
                    current_time = now.strftime("%I:%M %p").lstrip("0")  # Remove leading zero
                    
                    if is_alarm:
                        # For alarms, only include name if it's not auto-generated
                        if name and not name.startswith("alarm_"):
                            announcement = f"{name} alarm. It's {current_time}"
                            if message:
                                announcement += f". {message}"
                        else:
                            # Auto-generated alarm name, just announce time
                            announcement = f"It's {current_time}"
                            if message:
                                announcement += f". {message}"
                    else:
                        # For reminders, always include the name
                        announcement = f"Time to {name}. It's {current_time}"
                        if message:
                            announcement += f". {message}"
                    
                    _LOGGER.debug("Making announcement: %s", announcement)

                    # 2. Make TTS announcement
                    await self.hass.services.async_call(
                        "assist_satellite",
                        "announce",
                        {
                            "entity_id": satellite_entity_id,
                            "message": announcement
                        },
                        blocking=True
                    )

                    # 3. Wait for satellite to be idle
                    while not await self._is_satellite_idle(satellite_entity_id):
                        if self._stop_event and self._stop_event.is_set():
                            return
                        await asyncio.sleep(1)

                    # 4. Play ringtone
                    await self.hass.services.async_call(
                        "assist_satellite",
                        "announce",
                        {
                            "entity_id": satellite_entity_id,
                            "media_id": sound_file
                        },
                        blocking=True
                    )

                    # 5. Wait for one minute or until stopped
                    try:
                        if self._stop_event:
                            await asyncio.wait_for(self._stop_event.wait(), timeout=60)
                            break
                        else:
                            await asyncio.sleep(60)
                    except asyncio.TimeoutError:
                        continue

                except Exception as err:
                    _LOGGER.error("Error in announcement loop: %s", err)
                    await asyncio.sleep(5)

        except Exception as err:
            _LOGGER.error(
                "Error announcing on satellite %s: %s",
                satellite,
                str(err),
                exc_info=True
            )

    async def _is_satellite_idle(self, satellite_entity_id: str) -> bool:
        """Check if satellite is idle."""
        try:
            state = self.hass.states.get(satellite_entity_id)
            return state.state == "idle" if state else True
        except Exception:
            return True  # Assume idle if can't get state