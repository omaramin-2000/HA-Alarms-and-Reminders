"""Coordinator for scheduling alarms and reminders."""
import datetime
import logging
from typing import Dict, Any
import asyncio
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN  # Add this import at the top
from .entity import AlarmReminderEntity

_LOGGER = logging.getLogger(__name__)

class AlarmAndReminderCoordinator:
    """Coordinates scheduling of alarms and reminders."""
    
    def __init__(self, hass: HomeAssistant, media_handler, announcer):
        """Initialize coordinator."""
        self.hass = hass
        self.media_handler = media_handler
        self.announcer = announcer
        self._active_items: Dict[str, Dict[str, Any]] = {}
        self.async_add_entities = None  # Will be set during platform setup
        self._alarm_counter = 0
        self._reminder_counter = 0

    async def schedule_item(self, call: ServiceCall, is_alarm: bool, target: dict) -> None:
        """Schedule an alarm or reminder."""
        try:
            _LOGGER.debug("Scheduling %s with data: %s", "alarm" if is_alarm else "reminder", call.data)
            
            # Increment counter
            if is_alarm:
                self._alarm_counter += 1
                item_name = f"alarm_{self._alarm_counter}"
            else:
                self._reminder_counter += 1
                item_name = f"reminder_{self._reminder_counter}"

            time_input = call.data.get("time")
            date_input = call.data.get("date")
            message = call.data.get("message", "")
            repeat = call.data.get("repeat", "once")
            repeat_days = call.data.get("repeat_days", [])

            # Convert time input to datetime
            now = dt_util.now()
            if isinstance(time_input, str):
                try:
                    hour, minute = map(int, time_input.split(':'))
                    time_input = datetime.time(hour, minute)
                except ValueError as err:
                    _LOGGER.error("Invalid time format: %s", err)
                    return

            if date_input:
                scheduled_time = datetime.datetime.combine(date_input, time_input)
                scheduled_time = dt_util.as_local(scheduled_time)
            else:
                scheduled_time = datetime.datetime.combine(now.date(), time_input)
                scheduled_time = dt_util.as_local(scheduled_time)
                if scheduled_time < now:
                    scheduled_time = scheduled_time + datetime.timedelta(days=1)

            delay = (scheduled_time - now).total_seconds()
            if delay < 0:
                _LOGGER.warning("Scheduled time %s is in the past. Ignoring request.", scheduled_time)
                return

            # Store item info
            self._active_items[item_name] = {
                "scheduled_time": scheduled_time,
                "satellite": target.get("satellite"),
                "media_players": target.get("media_players", []),
                "message": message,
                "is_alarm": is_alarm,
                "repeat": repeat,
                "repeat_days": repeat_days,
                "status": "scheduled",
                "name": item_name
            }

            # Create entity for the alarm/reminder
            self.hass.states.async_set(
                f"{DOMAIN}.{item_name}",
                "scheduled",
                {
                    "scheduled_time": scheduled_time.isoformat(),
                    "satellite": target.get("satellite"),
                    "media_players": target.get("media_players"),
                    "message": message,
                    "is_alarm": is_alarm,
                    "repeat": repeat,
                    "repeat_days": repeat_days,
                    "status": "scheduled",
                    "friendly_name": item_name
                }
            )

            entity = AlarmReminderEntity(self.hass, item_name, self._active_items[item_name])
            self.hass.data[DOMAIN]["entities"].append(entity)

            # Add entity using the callback if available
            if self.async_add_entities is not None:
                self.async_add_entities([entity])

            _LOGGER.info(
                "Scheduled %s '%s' for %s (in %d seconds) on satellite '%s' and media players %s",
                "alarm" if is_alarm else "reminder",
                item_name,
                scheduled_time,
                delay,
                target.get("satellite"),
                target.get("media_players")
            )

            # Schedule the action
            self.hass.loop.call_later(
                delay,
                lambda: self.hass.async_create_task(self._trigger_item(item_name))
            )

            # Notify state change
            self.hass.bus.async_fire(f"{DOMAIN}_state_changed", {
                "type": "alarm" if is_alarm else "reminder",
                "action": "scheduled",
                "item_id": item_name,
                "scheduled_time": scheduled_time.isoformat(),
            })

            # Update sensors
            self.hass.bus.async_fire(f"{DOMAIN}_state_changed")
            
            _LOGGER.debug("Scheduled item: %s", self._active_items[item_name])
            
            return item_name

        except Exception as err:
            _LOGGER.error("Error scheduling: %s", err, exc_info=True)
            raise

    async def _trigger_item(self, item_id: str) -> None:
        """Trigger the scheduled item."""
        if item_id not in self._active_items:
            return

        try:
            item = self._active_items[item_id]
            item["status"] = "active"
            item["stop_event"] = asyncio.Event()

            # Start playback loop
            if item["satellite"]:
                await self._satellite_playback_loop(item)
            elif item["media_players"]:
                await self._media_player_playback_loop(item)

        except Exception as err:
            _LOGGER.error("Error triggering item %s: %s", item_id, err)
            item["status"] = "error"
            raise

    async def _satellite_playback_loop(self, item: dict) -> None:
        """Handle satellite playback loop."""
        while not item["stop_event"].is_set():
            try:
                # Wait for satellite to be idle
                while not await self._is_satellite_idle(item["satellite"]):
                    await asyncio.sleep(1)

                # Announce current time
                current_time = self._format_time()
                await self.announcer.make_announcement(
                    item["satellite"],
                    current_time,
                    item["message"],
                    item["is_alarm"]
                )

                # Wait for satellite to be idle again
                while not await self._is_satellite_idle(item["satellite"]):
                    await asyncio.sleep(1)

                # Play sound file
                await self.media_handler.play_sound(
                    item["satellite"],
                    [],  # No media players
                    item["is_alarm"],
                    item["message"]
                )

                # Wait 60 seconds before next announcement
                try:
                    await asyncio.wait_for(item["stop_event"].wait(), timeout=60)
                    break
                except asyncio.TimeoutError:
                    continue

            except Exception as err:
                _LOGGER.error("Error in satellite playback loop: %s", err)
                await asyncio.sleep(5)

    async def _media_player_playback_loop(self, item: dict) -> None:
        """Handle media player playback loop."""
        while not item["stop_event"].is_set():
            try:
                for media_player in item["media_players"]:
                    # Wait for media player to be idle
                    while not await self._is_media_player_idle(media_player):
                        await asyncio.sleep(1)

                    # Play TTS
                    current_time = self._format_time()
                    await self.hass.services.async_call(
                        "tts",
                        "speak",
                        {
                            "entity_id": media_player,
                            "message": f"It's {current_time}. {item['message']}"
                        },
                        blocking=True
                    )

                    # Wait for media player to be idle
                    while not await self._is_media_player_idle(media_player):
                        await asyncio.sleep(1)

                    # Play sound file
                    await self.media_handler.play_sound(
                        None,  # No satellite
                        [media_player],
                        item["is_alarm"],
                        item["message"]
                    )

                # Wait for completion or stop event
                try:
                    await asyncio.wait_for(item["stop_event"].wait(), timeout=60)
                    break
                except asyncio.TimeoutError:
                    continue

            except Exception as err:
                _LOGGER.error("Error in media player playback loop: %s", err)
                await asyncio.sleep(5)

    async def _is_satellite_idle(self, satellite: str) -> bool:
        """Check if satellite is idle."""
        state = self.hass.states.get(f"assist_satellite.{satellite}")
        return state.state == "idle" if state else True

    async def _is_media_player_idle(self, media_player: str) -> bool:
        """Check if media player is idle."""
        state = self.hass.states.get(media_player)
        return state.state in ["idle", "off"] if state else True

    def _format_time(self) -> str:
        """Format current time based on HA configuration."""
        now = dt_util.now()
        time_format = self.hass.config.time_format
        if time_format == "12":
            return now.strftime("%I:%M %p")
        return now.strftime("%H:%M")

    async def delete_item(self, item_id: str) -> None:
        """Delete an alarm/reminder."""
        if item_id in self._active_items:
            # Stop if active
            if self._active_items[item_id].get("stop_event"):
                self._active_items[item_id]["stop_event"].set()
            
            # Remove from active items
            del self._active_items[item_id]
            
            # Remove entity
            self.hass.states.async_remove(f"{DOMAIN}.{item_id}")
            
            # Update sensors
            self.hass.bus.async_fire(f"{DOMAIN}_state_changed")

    async def stop_item(self, item_id: str, is_alarm: bool) -> None:
        """Stop an active item."""
        if item_id in self._active_items:
            if self._active_items[item_id].get("stop_event"):
                self._active_items[item_id]["stop_event"].set()
            self._active_items[item_id]["status"] = "stopped"
            # Update entity state
            self.hass.states.async_set(
                f"{DOMAIN}.{item_id}",
                "stopped",
                self._active_items[item_id]
            )

    async def snooze_item(self, item_id: str, minutes: int, is_alarm: bool) -> None:
        """Snooze an active item."""
        if item_id in self._active_items:
            await self.media_handler.snooze_alarm(item_id, minutes)
