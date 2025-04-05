"""Coordinator for scheduling alarms and reminders."""
import datetime
from dateutil import parser
import logging
from homeassistant.core import HomeAssistant, ServiceCall

_LOGGER = logging.getLogger(__name__)

class AlarmAndReminderCoordinator:
    """Coordinates scheduling of alarms and reminders."""
    
    def __init__(self, hass: HomeAssistant, media_handler, announcer):
        """Initialize coordinator."""
        self.hass = hass
        self.media_handler = media_handler
        self.announcer = announcer
        self._active_items = {}

    async def schedule_item(self, call: ServiceCall, is_alarm: bool, target: str) -> None:
        """Schedule an alarm or reminder."""
        time_input = call.data.get("time")
        date_input = call.data.get("date")
        message = call.data.get("message")
        repeat = call.data.get("repeat", "once")
        repeat_days = call.data.get("repeat_days", [])

        # Convert time input to datetime
        now = datetime.datetime.now()
        scheduled_time = datetime.datetime.combine(
            date_input or now.date(),
            time_input
        )

        # If scheduled time is in the past and no date was specified, schedule for tomorrow
        if scheduled_time < now and not date_input:
            scheduled_time = scheduled_time + datetime.timedelta(days=1)

        delay = (scheduled_time - now).total_seconds()
        if delay < 0:
            _LOGGER.warning("Scheduled time is in the past. Ignoring the request.")
            return

        # Generate unique ID for this item
        item_id = f"{'alarm' if is_alarm else 'reminder'}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Store item info
        self._active_items[item_id] = {
            "scheduled_time": scheduled_time,
            "target": target,
            "message": message,
            "is_alarm": is_alarm,
            "repeat": repeat,
            "repeat_days": repeat_days
        }

        item_type = "alarm" if is_alarm else "reminder"
        _LOGGER.info(
            f"Setting {item_type} for %s (in %s seconds) on '%s'", 
            scheduled_time, delay, target
        )

        # Schedule the action
        self.hass.loop.call_later(
            delay, 
            lambda: self.hass.async_create_task(
                self._trigger_item(item_id)
            )
        )

    async def _trigger_item(self, item_id: str) -> None:
        """Trigger the scheduled item."""
        if item_id not in self._active_items:
            return

        item = self._active_items[item_id]
        time_str = item["scheduled_time"].strftime("%I:%M %p")
        
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