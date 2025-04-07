"""Coordinator for scheduling alarms and reminders."""
import datetime
import logging
from typing import Dict, Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.util import dt as dt_util
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

    async def schedule_item(self, call: ServiceCall, is_alarm: bool, target: dict) -> None:
        """Schedule an alarm or reminder."""
        try:
            _LOGGER.debug("Scheduling %s with data: %s", "alarm" if is_alarm else "reminder", call.data)
            
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

            # Generate unique ID
            item_id = f"{'alarm' if is_alarm else 'reminder'}_{now.strftime('%Y%m%d%H%M%S')}"
            
            # Store item info
            self._active_items[item_id] = {
                "scheduled_time": scheduled_time,
                "satellite": target.get("satellite"),
                "media_players": target.get("media_players", []),
                "message": message,
                "is_alarm": is_alarm,
                "repeat": repeat,
                "repeat_days": repeat_days,
                "status": "scheduled"
            }

            # Create entity for the alarm/reminder
            self.hass.states.async_set(
                f"{DOMAIN}.{item_id}",
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
                }
            )

            entity = AlarmReminderEntity(self.hass, item_id, self._active_items[item_id])
            self.hass.data[DOMAIN]["entities"].append(entity)
            self.hass.helpers.entity_platform.async_add_entities([entity])

            _LOGGER.info(
                "Scheduled %s '%s' for %s (in %d seconds) on satellite '%s' and media players %s",
                "alarm" if is_alarm else "reminder",
                item_id,
                scheduled_time,
                delay,
                target.get("satellite"),
                target.get("media_players")
            )

            # Schedule the action
            self.hass.loop.call_later(
                delay,
                lambda: self.hass.async_create_task(self._trigger_item(item_id))
            )

            # Notify state change
            self.hass.bus.async_fire(f"{DOMAIN}_state_changed", {
                "type": "alarm" if is_alarm else "reminder",
                "action": "scheduled",
                "item_id": item_id,
                "scheduled_time": scheduled_time.isoformat(),
            })

            # Update sensors
            self.hass.bus.async_fire(f"{DOMAIN}_state_changed")
            
            _LOGGER.debug("Scheduled item: %s", self._active_items[item_id])
            
            return item_id

        except Exception as err:
            _LOGGER.error("Error scheduling: %s", err, exc_info=True)
            raise

    async def _trigger_item(self, item_id: str) -> None:
        """Trigger the scheduled item."""
        if item_id not in self._active_items:
            _LOGGER.warning("Item %s not found in active items", item_id)
            return

        try:
            item = self._active_items[item_id]
            _LOGGER.debug("Triggering item: %s", item)
            time_str = item["scheduled_time"].strftime("%I:%M %p")
            
            _LOGGER.info(
                "Triggering %s '%s' scheduled for %s on target '%s'",
                "alarm" if item["is_alarm"] else "reminder",
                item_id,
                time_str,
                item["target"]
            )

            item["status"] = "active"
            
            # Play sound and make announcement
            await self.media_handler.play_sound(
                item["target"],
                item["is_alarm"],
                is_satellite="satellite" in item["target"],
                alarm_id=item_id
            )
            
            if "satellite" in item["target"]:
                await self.announcer.make_announcement(
                    item["target"],
                    time_str,
                    item["message"],
                    item["is_alarm"]
                )

            # Handle repeat logic
            if item["repeat"] != "once":
                await self._schedule_next_occurrence(item_id)
            else:
                item["status"] = "completed"

        except Exception as err:
            _LOGGER.error("Error triggering item %s: %s", item_id, err, exc_info=True)
            item["status"] = "error"
            raise

    async def _schedule_next_occurrence(self, item_id: str) -> None:
        """Schedule the next occurrence of a repeating item."""
        # Implementation for repeat logic
        pass  # We'll implement this later

    async def stop_item(self, item_id: str, is_alarm: bool) -> None:
        """Stop an active item."""
        if item_id in self._active_items:
            await self.media_handler.stop_alarm(item_id)
            del self._active_items[item_id]

    async def snooze_item(self, item_id: str, minutes: int, is_alarm: bool) -> None:
        """Snooze an active item."""
        if item_id in self._active_items:
            await self.media_handler.snooze_alarm(item_id, minutes)
