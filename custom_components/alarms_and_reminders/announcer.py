"""Handle announcements and sounds on satellites using direct entity methods."""
import logging
import asyncio
import shutil
from pathlib import Path
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.components.assist_satellite import (
    AssistSatelliteEntity,
    AssistSatelliteEntityFeature,
)
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)


class AudioFileCopier:
    """Copy built-in audio files from component to HA www folder."""

    @staticmethod
    async def copy_audio_files(hass: HomeAssistant) -> None:
        """Copy built-in audio files from component www folder to HA www folder."""
        try:
            component_path = Path(__file__).parent / "www" / "alarm&reminder_sounds"
            config_path = Path(hass.config.path())
            dest_path = config_path / "www" / "alarm&reminder_sounds"

            await hass.async_add_executor_job(
                lambda: dest_path.mkdir(parents=True, exist_ok=True)
            )
            await hass.async_add_executor_job(
                lambda: (dest_path / "alarms").mkdir(exist_ok=True)
            )
            await hass.async_add_executor_job(
                lambda: (dest_path / "reminders").mkdir(exist_ok=True)
            )

            # Copy alarm files
            alarms_dir = component_path / "alarms"
            if await hass.async_add_executor_job(alarms_dir.exists):
                alarm_files = await hass.async_add_executor_job(
                    lambda: list(alarms_dir.glob("*"))
                )
                for alarm_file in alarm_files:
                    if await hass.async_add_executor_job(alarm_file.is_file):
                        dest_file = dest_path / "alarms" / alarm_file.name
                        await hass.async_add_executor_job(
                            shutil.copy2, str(alarm_file), str(dest_file)
                        )
                        _LOGGER.debug("Copied alarm file: %s", alarm_file.name)

            # Copy reminder files
            reminders_dir = component_path / "reminders"
            if await hass.async_add_executor_job(reminders_dir.exists):
                reminder_files = await hass.async_add_executor_job(
                    lambda: list(reminders_dir.glob("*"))
                )
                for reminder_file in reminder_files:
                    if await hass.async_add_executor_job(reminder_file.is_file):
                        dest_file = dest_path / "reminders" / reminder_file.name
                        await hass.async_add_executor_job(
                            shutil.copy2, str(reminder_file), str(dest_file)
                        )
                        _LOGGER.debug("Copied reminder file: %s", reminder_file.name)

            _LOGGER.info("Audio files copied to %s", dest_path)

        except Exception as err:
            _LOGGER.error("Error copying audio files: %s", err, exc_info=True)


class Announcer:
    """Handles announcements on satellites using direct entity methods for looping."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize announcer."""
        self.hass = hass
    
    async def announce_on_satellite(
        self,
        satellite: str,
        message: str,
        sound_file: str,
        stop_event: asyncio.Event,
        name: str,
        is_alarm: bool = False
    ) -> None:
        """Ring alarm/reminder on satellite using direct entity announcement methods.
        
        Directly interfaces with the satellite entity to:
        1. Resolve TTS message to audio URL
        2. Call async_announce() in a loop with TTS + ringtone
        3. Keep satellite in RESPONDING state throughout
        4. Return to IDLE only when stopped
        
        Args:
            satellite: Satellite entity ID
            message: Optional custom message
            sound_file: Full URL to ringtone file
            stop_event: Event to stop the announcement loop
            name: Alarm/reminder name
            is_alarm: Whether this is an alarm (True) or reminder (False)
        """
        satellite_entity_id = (
            satellite if satellite.startswith("assist_satellite.")
            else f"assist_satellite.{satellite}"
        )
        
        # Get the satellite entity
        satellite_entity = self._get_satellite_entity(satellite_entity_id)
        if not satellite_entity:
            _LOGGER.error("Satellite entity %s not found", satellite_entity_id)
            return
        
        cycle_count = 0
        start_time = dt_util.now()
        
        _LOGGER.info(
            "Starting announcement loop on %s - Name: %s, Type: %s",
            satellite_entity_id,
            name,
            "alarm" if is_alarm else "reminder"
        )
        
        try:
            # Cancel any running pipeline on the satellite
            await satellite_entity._cancel_running_pipeline()
            
            # Check if satellite is already announcing
            if satellite_entity._is_announcing:
                _LOGGER.warning("Satellite %s is already announcing, waiting...", satellite_entity_id)
                # Wait a bit and retry
                await asyncio.sleep(1)
                if satellite_entity._is_announcing:
                    _LOGGER.error("Satellite %s still busy", satellite_entity_id)
                    return
            
            # Set satellite to announcing mode and RESPONDING state
            satellite_entity._is_announcing = True
            satellite_entity._set_state("responding")  # AssistSatelliteState.RESPONDING
            
            try:
                while not stop_event.is_set():
                    cycle_count += 1
                    
                    # Format announcement message (full on first cycle only)
                    announcement_text = self._format_announcement(
                        name=name,
                        is_alarm=is_alarm,
                        message=message if cycle_count == 1 else None,
                        is_full=(cycle_count == 1)
                    )
                    
                    _LOGGER.debug(
                        "Cycle %d: Announcing '%s' on %s",
                        cycle_count,
                        announcement_text,
                        satellite_entity_id
                    )
                    
                    # Step 1: Resolve TTS message to announcement object
                    try:
                        tts_announcement = await satellite_entity._resolve_announcement_media_id(
                            message=announcement_text,
                            media_id=None,  # Let it generate TTS
                            preannounce_media_id=None  # No preannounce chime
                        )
                    except Exception as err:
                        _LOGGER.error("Error resolving TTS announcement: %s", err)
                        break
                    
                    # Step 2: Play TTS announcement
                    try:
                        announce_task = asyncio.create_task(
                            satellite_entity.async_announce(tts_announcement)
                        )
                        
                        # Race between announcement completion and stop event
                        done, pending = await asyncio.wait(
                            [announce_task, asyncio.create_task(stop_event.wait())],
                            return_when=asyncio.FIRST_COMPLETED,
                            timeout=30.0
                        )
                        
                        # Cancel pending tasks
                        for task in pending:
                            task.cancel()
                        
                        # Check if stopped
                        if stop_event.is_set():
                            _LOGGER.info("Stop event detected during TTS")
                            break
                        
                        # Check if announcement task raised an exception
                        if announce_task in done:
                            try:
                                await announce_task  # Raise any exceptions
                            except Exception as err:
                                _LOGGER.error("TTS announcement failed: %s", err)
                                break
                        
                    except asyncio.TimeoutError:
                        _LOGGER.warning("TTS announcement timed out")
                        break
                    
                    # Check stop event before playing ringtone
                    if stop_event.is_set():
                        break
                    
                    # Step 3: Resolve ringtone media to announcement object
                    _LOGGER.debug("Cycle %d: Playing ringtone", cycle_count)
                    
                    try:
                        ringtone_announcement = await satellite_entity._resolve_announcement_media_id(
                            message="",  # No text for ringtone
                            media_id=sound_file,  # Direct media URL
                            preannounce_media_id=None
                        )
                    except Exception as err:
                        _LOGGER.error("Error resolving ringtone: %s", err)
                        break
                    
                    # Step 4: Play ringtone
                    try:
                        ringtone_task = asyncio.create_task(
                            satellite_entity.async_announce(ringtone_announcement)
                        )
                        
                        # Race between ringtone completion and stop event
                        done, pending = await asyncio.wait(
                            [ringtone_task, asyncio.create_task(stop_event.wait())],
                            return_when=asyncio.FIRST_COMPLETED,
                            timeout=60.0
                        )
                        
                        # Cancel pending tasks
                        for task in pending:
                            task.cancel()
                        
                        # Check if stopped
                        if stop_event.is_set():
                            _LOGGER.info("Stop event detected during ringtone")
                            break
                        
                        # Check if ringtone task raised an exception
                        if ringtone_task in done:
                            try:
                                await ringtone_task
                            except Exception as err:
                                _LOGGER.error("Ringtone playback failed: %s", err)
                                break
                        
                    except asyncio.TimeoutError:
                        _LOGGER.warning("Ringtone playback timed out")
                        break
                    
                    _LOGGER.debug("Cycle %d completed", cycle_count)
            
            finally:
                # Always reset satellite state when done
                satellite_entity._is_announcing = False
                satellite_entity._set_state("idle")  # AssistSatelliteState.IDLE
            
            duration = dt_util.now() - start_time
            _LOGGER.info(
                "Announcement loop ended - Cycles: %d, Duration: %s",
                cycle_count,
                duration
            )
            
        except Exception as err:
            _LOGGER.error(
                "Error in announcement loop for %s: %s",
                satellite_entity_id,
                err,
                exc_info=True
            )
            # Ensure we reset state on error
            try:
                satellite_entity._is_announcing = False
                satellite_entity._set_state("idle")
            except Exception:
                pass
    
    def _get_satellite_entity(self, entity_id: str) -> Optional[AssistSatelliteEntity]:
        """Get the satellite entity from the entity registry.
        
        Args:
            entity_id: The satellite entity ID
            
        Returns:
            The satellite entity or None if not found
        """
        try:
            # Get all entity platforms
            from homeassistant.helpers import entity_platform
            
            platforms = entity_platform.async_get_platforms(self.hass, "assist_satellite")
            
            for platform in platforms:
                for entity in platform.entities.values():
                    if entity.entity_id == entity_id:
                        return entity
            
            _LOGGER.error("Satellite entity %s not found in platforms", entity_id)
            return None
            
        except Exception as err:
            _LOGGER.error("Error getting satellite entity: %s", err)
            return None
    
    def _format_announcement(
        self,
        name: str,
        is_alarm: bool,
        message: str = None,
        is_full: bool = True
    ) -> str:
        """Format announcement message.
        
        Args:
            name: Alarm/reminder name
            is_alarm: Whether this is an alarm (True) or reminder (False)
            message: Optional custom message (only for full announcements)
            is_full: If True, use full announcement with message; if False, just name + time
        
        Returns:
            Formatted announcement string
        """
        now = dt_util.now()
        current_time = now.strftime("%I:%M %p").lstrip("0")
        
        if is_alarm:
            if name and not name.startswith("alarm_"):
                announcement = f"{name} alarm. It's {current_time}"
            else:
                announcement = f"Alarm. It's {current_time}"
            
            if is_full and message:
                announcement += f". {message}"
        else:
            announcement = f"Time to {name}. It's {current_time}"
            
            if is_full and message:
                announcement += f". {message}"
        
        return announcement
