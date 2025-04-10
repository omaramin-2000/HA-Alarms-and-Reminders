"""Handle announcements and sounds on satellites."""
import logging
import asyncio
from datetime import datetime
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class Announcer:
    """Handles announcements and sounds on satellites."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize announcer."""
        self.hass = hass
        self._stop_event = None

    async def announce_on_satellite(self, satellite: str, message: str, sound_file: str, stop_event=None) -> None:
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
                    # 1. First make the TTS announcement
                    current_time = datetime.now().strftime("%I:%M %p")
                    announcement = f"It's {current_time}. {message}" if message else f"It's {current_time}"
                    
                    await self.hass.services.async_call(
                        "assist_satellite",
                        "announce",
                        {
                            "entity_id": satellite_entity_id,
                            "message": announcement
                        },
                        blocking=True
                    )

                    # 2. Wait for satellite to be idle
                    while not await self._is_satellite_idle(satellite_entity_id):
                        if self._stop_event and self._stop_event.is_set():
                            return
                        await asyncio.sleep(1)

                    # 3. Play ringtone
                    await self.hass.services.async_call(
                        "assist_satellite",
                        "announce",
                        {
                            "entity_id": satellite_entity_id,
                            "media_id": sound_file
                        },
                        blocking=True
                    )

                    # 4. Wait for one minute or until stopped
                    try:
                        if self._stop_event:
                            await asyncio.wait_for(self._stop_event.wait(), timeout=60)
                            break
                        else:
                            await asyncio.sleep(60)
                    except asyncio.TimeoutError:
                        continue  # Continue to next iteration after 1 minute

                except Exception as err:
                    _LOGGER.error("Error in announcement loop: %s", err)
                    await asyncio.sleep(5)  # Wait before retry on error

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