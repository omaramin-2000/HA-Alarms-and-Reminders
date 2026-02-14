"""Coordinator for scheduling alarms and reminders."""
import logging
import asyncio
import re
import os
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import async_get as get_entity_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.network import get_url

from .const import (
    DOMAIN,
    DEFAULT_SNOOZE_MINUTES,
    DEFAULT_NAME,
    EVENT_ITEM_CREATED,
    EVENT_ITEM_UPDATED,
    EVENT_ITEM_DELETED,
    EVENT_DASHBOARD_UPDATED,
)
from .storage import AlarmReminderStorage

_LOGGER = logging.getLogger(__name__)

__all__ = ["AlarmAndReminderCoordinator"]

# Dispatcher event names (used by switch platform to add/remove/update entities)
ITEM_CREATED = f"{DOMAIN}_item_created"
ITEM_UPDATED = f"{DOMAIN}_item_updated"
ITEM_DELETED = f"{DOMAIN}_item_deleted"
DASHBOARD_UPDATED = f"{DOMAIN}_dashboard_updated"


class AlarmAndReminderCoordinator(DataUpdateCoordinator):
    """Coordinates scheduling of alarms and reminders."""
    
    def __init__(self, hass: HomeAssistant, media_handler, announcer, config_entry_id: str = None):
        """Initialize coordinator."""
        self.hass = hass
        self.media_handler = media_handler
        self.announcer = announcer
        self.config_entry_id = config_entry_id 
        self._active_items: Dict[str, Dict[str, Any]] = {}
        self._stop_events: Dict[str, asyncio.Event] = {}
        self._trigger_cancel_funcs: Dict[str, Callable] = {}  # Track scheduled triggers
        self.storage = AlarmReminderStorage(hass)
        
        # Load existing items from states
        _LOGGER.debug("Initializing coordinator")
        try:
            for state in hass.states.async_all():
                if not state.entity_id.startswith(f"{DOMAIN}."):
                    continue

                item_id = state.entity_id.split(".")[-1]
                attributes = dict(state.attributes)
                
                if "scheduled_time" in attributes:
                    try:
                        if isinstance(attributes["scheduled_time"], str):
                            attributes["scheduled_time"] = dt_util.parse_datetime(
                                attributes["scheduled_time"]
                            )
                    except Exception as err:
                        _LOGGER.error("Error parsing scheduled_time: %s", err)

                self._active_items[item_id] = attributes
                if state.state == "active":
                    self._stop_events[item_id] = asyncio.Event()

                _LOGGER.debug("Loaded item: %s", item_id)

        except Exception as err:
            _LOGGER.error("Error loading existing items: %s", err, exc_info=True)
        
        # Ensure domain data structure exists
        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = {}
        
        # Notification action mapping
        self._notification_listener = hass.bus.async_listen(
            "mobile_app_notification_action", self._on_mobile_notification_action
        )
        self._notification_tag_map: Dict[str, str] = {}

    def _get_next_available_id(self, prefix: str) -> str:
        """Get next available ID for alarms."""
        counter = 1
        while True:
            potential_id = f"{prefix}_{counter}"
            if potential_id not in self._active_items:
                return potential_id
            counter += 1

    def _schedule_item(self, item_id: str, scheduled_time: datetime) -> None:
        """Schedule an item to trigger at a specific time.
        
        This is used by switch.py to re-schedule after enable/edit.
        """
        try:
            # Cancel existing trigger if any
            if item_id in self._trigger_cancel_funcs:
                try:
                    self._trigger_cancel_funcs[item_id]()
                except Exception as e:
                    _LOGGER.debug("Error canceling old trigger for %s: %s", item_id, e)
                del self._trigger_cancel_funcs[item_id]
            
            # Create a safe callback that properly handles the event loop
            async def _trigger_callback(now_dt: datetime) -> None:
                """Callback to trigger item - safe for any thread."""
                try:
                    await self._trigger_item(item_id)
                except Exception as err:
                    _LOGGER.error("Error in trigger callback for %s: %s", item_id, err)
            
            # Schedule new trigger with async callback
            cancel_func = async_track_point_in_time(
                self.hass,
                _trigger_callback,
                scheduled_time,
            )
            self._trigger_cancel_funcs[item_id] = cancel_func
            
            _LOGGER.debug("Scheduled item %s for %s", item_id, scheduled_time)
            
        except Exception as err:
            _LOGGER.error("Error scheduling item %s: %s", item_id, err, exc_info=True)

    async def async_load_items(self) -> None:
        """Load items from storage and restore internal state."""
        try:
            self._active_items = await self.storage.async_load()
            _LOGGER.debug("Loaded items from storage: %d items", len(self._active_items))

            now = dt_util.now()

            for item_id, item in list(self._active_items.items()):
                # Normalize scheduled_time if string
                if "scheduled_time" in item and isinstance(item["scheduled_time"], str):
                    item["scheduled_time"] = dt_util.parse_datetime(item["scheduled_time"])

                status = item.get("status", "scheduled")

                if status == "active":
                    self._stop_events[item_id] = asyncio.Event()
                    self.hass.async_create_task(
                        self._start_playback(item_id),
                        name=f"playback_{item_id}"
                    )
                elif status == "scheduled" and item.get("scheduled_time"):
                    sched = item["scheduled_time"]
                    if isinstance(sched, str):
                        sched = dt_util.parse_datetime(sched)
                        item["scheduled_time"] = sched

                    if isinstance(sched, datetime) and sched > now and item.get("enabled", True):
                        self._schedule_item(item_id, sched)

            self._update_dashboard_state()
            async_dispatcher_send(self.hass, DASHBOARD_UPDATED)

        except Exception as err:
            _LOGGER.error("Error loading items: %s", err, exc_info=True)
        
    async def schedule_item(self, call: ServiceCall, is_alarm: bool, target: dict) -> None:
        """Schedule an alarm or reminder."""
        try:
            now = dt_util.now()

            time_input = call.data.get("time")
            date_input = call.data.get("date")
            message = call.data.get("message", "")
            supplied_name = call.data.get("name")

            # Determine item ID and display name
            if is_alarm:
                if supplied_name:
                    item_name = supplied_name.replace(" ", "_")
                    display_name = supplied_name
                    if item_name in self._active_items:
                        item_name = self._get_next_available_id("alarm")
                        display_name = item_name
                else:
                    item_name = self._get_next_available_id("alarm")
                    display_name = item_name
            else:
                if not supplied_name:
                    raise ValueError("Reminders require a name")
                item_name = supplied_name.replace(" ", "_")
                display_name = supplied_name
                if item_name in self._active_items:
                    raise ValueError(f"Reminder already exists: {supplied_name}")

            # Parse time
            if isinstance(time_input, str):
                time_str = time_input.split("T")[-1]
                parsed = dt_util.parse_time(time_str)
                if parsed is None:
                    raise ValueError(f"Invalid time format: {time_input}")
                time_obj = parsed
            elif isinstance(time_input, datetime):
                time_obj = time_input.time()
            else:
                time_obj = time_input or now.time()

            # Combine date and time
            if date_input:
                scheduled_time = datetime.combine(date_input, time_obj)
            else:
                scheduled_time = datetime.combine(now.date(), time_obj)

            scheduled_time = dt_util.as_local(scheduled_time)

            # If time is in past, push to next day
            if scheduled_time <= now:
                scheduled_time = scheduled_time + timedelta(days=1)

            # Build item
            item = {
                "scheduled_time": scheduled_time,
                "satellite": target.get("satellite"),
                "message": message,
                "is_alarm": is_alarm,
                "repeat": call.data.get("repeat", "once"),
                "repeat_days": call.data.get("repeat_days", []),
                "status": "scheduled",
                "name": display_name,
                "entity_id": item_name,
                "unique_id": item_name,
                "enabled": True,
                # Resolve sound file from ringtone parameter or custom file
                "sound_file": self._resolve_sound_file(
                    ringtone=call.data.get("ringtone"),
                    sound_file=call.data.get("sound_file"),
                    is_alarm=is_alarm
                ),
                "notify_device": call.data.get("notify_device"),
            }

            self._active_items[item_name] = item
            await self.storage.async_save(self._active_items)

            # Register entity in entity registry immediately
            entity_registry = get_entity_registry(self.hass)
            entity_id = f"switch.{item_name}"
            try:
                entity_registry.async_get_or_create(
                    domain="switch",
                    platform=DOMAIN,
                    unique_id=item_name,
                    suggested_object_id=item_name,
                    config_entry_id=self.config_entry_id,  # ← Use the stored config_entry_id
                )
                _LOGGER.debug("Registered entity %s in registry", entity_id)
            except Exception as err:
                _LOGGER.debug("Could not register entity %s: %s", entity_id, err)

            # Schedule the trigger
            self._schedule_item(item_name, scheduled_time)

            self._update_dashboard_state()
            async_dispatcher_send(self.hass, DASHBOARD_UPDATED)
            async_dispatcher_send(self.hass, ITEM_CREATED, item_name, item)

            _LOGGER.info(
                "Scheduled %s %s for %s",
                "alarm" if is_alarm else "reminder",
                item_name,
                scheduled_time
            )

        except Exception as err:
            _LOGGER.error("Error scheduling: %s", err, exc_info=True)
            raise

    def _calculate_next_trigger(self, item: dict) -> Optional[datetime]:
        """Calculate the next trigger time for an item based on repeat type and state.
        
        For 'once' items:
            - If not yet triggered, return scheduled_time
            - If already triggered/stopped, calculate based on current date + set time
            - If that time has passed today, return tomorrow at set time
        
        For repeated items:
            - Return the next scheduled occurrence based on repeat pattern
        
        Returns:
            datetime of next trigger, or None if unable to calculate
        """
        try:
            repeat = item.get("repeat", "once")
            scheduled_time = item.get("scheduled_time")
            status = item.get("status", "scheduled")
            
            if not isinstance(scheduled_time, datetime):
                if isinstance(scheduled_time, str):
                    scheduled_time = dt_util.parse_datetime(scheduled_time)
                else:
                    return None
            
            now = dt_util.now()
            
            # For 'once' items, calculate based on current date + set time
            if repeat == "once":
                # Get the time part from scheduled_time
                set_time = scheduled_time.time()
                today_at_set_time = datetime.combine(now.date(), set_time)
                today_at_set_time = dt_util.as_local(today_at_set_time)
                
                # If today's time hasn't passed, trigger is today
                if today_at_set_time > now:
                    return today_at_set_time
                else:
                    # If today's time has passed, trigger is tomorrow
                    tomorrow_at_set_time = today_at_set_time + timedelta(days=1)
                    return tomorrow_at_set_time
            
            # For daily repeats
            elif repeat == "daily":
                set_time = scheduled_time.time()
                today_at_set_time = datetime.combine(now.date(), set_time)
                today_at_set_time = dt_util.as_local(today_at_set_time)
                
                if today_at_set_time > now:
                    return today_at_set_time
                else:
                    tomorrow_at_set_time = today_at_set_time + timedelta(days=1)
                    return tomorrow_at_set_time
            
            # For weekday repeats
            elif repeat == "weekdays":
                set_time = scheduled_time.time()
                current_date = now.date()
                
                # Check today first
                if current_date.weekday() < 5:  # Monday=0, Friday=4
                    today_at_set_time = datetime.combine(current_date, set_time)
                    today_at_set_time = dt_util.as_local(today_at_set_time)
                    if today_at_set_time > now:
                        return today_at_set_time
                
                # Find next weekday
                days_ahead = 0
                current_weekday = current_date.weekday()
                if current_weekday < 5:
                    days_ahead = 1
                else:
                    # Saturday=5, Sunday=6
                    days_ahead = 7 - current_weekday
                
                next_weekday = current_date + timedelta(days=days_ahead)
                next_trigger = datetime.combine(next_weekday, set_time)
                return dt_util.as_local(next_trigger)
            
            # For weekend repeats
            elif repeat == "weekends":
                set_time = scheduled_time.time()
                current_date = now.date()
                current_weekday = current_date.weekday()
                
                # Check today first
                if current_weekday >= 5:  # Saturday=5, Sunday=6
                    today_at_set_time = datetime.combine(current_date, set_time)
                    today_at_set_time = dt_util.as_local(today_at_set_time)
                    if today_at_set_time > now:
                        return today_at_set_time
                
                # Find next weekend day
                if current_weekday < 5:
                    days_ahead = 5 - current_weekday
                else:
                    days_ahead = 7 - current_weekday + 5
                
                next_weekend = current_date + timedelta(days=days_ahead)
                next_trigger = datetime.combine(next_weekend, set_time)
                return dt_util.as_local(next_trigger)
            
            # For weekly repeats with specific days
            elif repeat == "weekly":
                repeat_days = item.get("repeat_days", [])
                if not repeat_days:
                    return None
                
                set_time = scheduled_time.time()
                current_date = now.date()
                current_weekday = current_date.weekday()
                
                # Check today first
                if current_weekday in repeat_days:
                    today_at_set_time = datetime.combine(current_date, set_time)
                    today_at_set_time = dt_util.as_local(today_at_set_time)
                    if today_at_set_time > now:
                        return today_at_set_time
                
                # Find next occurrence
                for days_ahead in range(1, 8):
                    next_date = current_date + timedelta(days=days_ahead)
                    if next_date.weekday() in repeat_days:
                        next_trigger = datetime.combine(next_date, set_time)
                        return dt_util.as_local(next_trigger)
                
                return None
            
            # For custom repeats, fall back to scheduled_time
            elif repeat == "custom":
                return scheduled_time
            
            # Default: return original scheduled_time
            return scheduled_time
        
        except Exception as err:
            _LOGGER.error("Error calculating next trigger: %s", err, exc_info=True)
            return item.get("scheduled_time")

    async def _trigger_item(self, item_id: str) -> None:
        """Trigger the scheduled item."""
        if item_id not in self._active_items:
            return

        try:
            item = self._active_items[item_id]

            # Check if item is enabled
            if not item.get("enabled", True):
                _LOGGER.debug("Item %s is disabled, skipping trigger", item_id)
                return

            item["status"] = "active"
            self._active_items[item_id] = item
            await self.storage.async_save(self._active_items)

            self._update_dashboard_state()
            async_dispatcher_send(self.hass, DASHBOARD_UPDATED)
            async_dispatcher_send(self.hass, ITEM_UPDATED, item_id, item)

            stop_event = asyncio.Event()
            self._stop_events[item_id] = stop_event

            # Send notification if configured
            if item.get("notify_device"):
                self._notification_tag_map[item_id] = item_id
                self.hass.async_create_task(self._send_notification(item_id, item))

            # Start playback
            self.hass.async_create_task(
                self._start_playback(item_id),
                name=f"playback_{item_id}"
            )

        except Exception as err:
            _LOGGER.error("Error triggering item %s: %s", item_id, err, exc_info=True)
            if item_id in self._active_items:
                item = self._active_items[item_id]
                item["status"] = "error"
                self._active_items[item_id] = item
                self.hass.async_create_task(self.storage.async_save(self._active_items))
                self._update_dashboard_state()
                async_dispatcher_send(self.hass, ITEM_UPDATED, item_id, self._active_items[item_id])

    async def _start_playback(self, item_id: str) -> None:
        """Start playback for active item."""
        try:
            item = self._active_items.get(item_id)
            if not item:
                _LOGGER.debug("Item %s not found", item_id)
                return

            stop_event = self._stop_events.get(item_id)
            if not stop_event:
                stop_event = asyncio.Event()
                self._stop_events[item_id] = stop_event

            if item.get("satellite"):
                await self._satellite_playback_loop(item, stop_event)
            else:
                _LOGGER.debug("No satellite configured for item %s, skipping satellite announcement", item_id)

            # Update status when playback ends based on repeat type
            if item_id in self._active_items:
                if self._active_items[item_id].get("status") == "active":
                    item = self._active_items[item_id]
                    repeat = item.get("repeat", "once")
                    
                    # For 'once' items, disable the switch after completion
                    if repeat == "once":
                        item["status"] = "completed"
                        item["enabled"] = False  # Switch will turn off
                    else:
                        # For repeated items, keep them enabled and reschedule
                        item["status"] = "stopped"
                        
                        # Calculate next trigger
                        next_trigger = self._calculate_next_trigger(item)
                        if next_trigger:
                            item["scheduled_time"] = next_trigger
                            # Schedule the next trigger
                            self._schedule_item(item_id, next_trigger)
                            _LOGGER.debug("Rescheduled recurring item %s for %s", item_id, next_trigger)
                    
                    item["last_stopped"] = dt_util.now().isoformat()
                    self._active_items[item_id] = item
                    await self.storage.async_save(self._active_items)
                    self._update_dashboard_state()
                    async_dispatcher_send(self.hass, ITEM_UPDATED, item_id, self._active_items[item_id])

            self._notification_tag_map.pop(item_id, None)
            self._stop_events.pop(item_id, None)

        except Exception as err:
            _LOGGER.error("Error in playback for %s: %s", item_id, err, exc_info=True)
            if item_id in self._active_items:
                self._active_items[item_id]["status"] = "error"
                self.hass.async_create_task(self.storage.async_save(self._active_items))
                async_dispatcher_send(self.hass, ITEM_UPDATED, item_id, self._active_items[item_id])

    async def _satellite_playback_loop(self, item: dict, stop_event: asyncio.Event) -> None:
        """Playback loop with duration tracking and state monitoring."""
        try:
            satellite = item.get("satellite")
            if not satellite:
                _LOGGER.debug("No satellite configured, skipping playback")
                return

            await self.announcer.announce_on_satellite(
                satellite=satellite,
                message=item.get("message", ""),
                sound_file=item.get("sound_file"),
                stop_event=stop_event,
                name=item.get("name"),
                is_alarm=item.get("is_alarm", False)
            )

        except Exception as err:
            _LOGGER.error("Satellite playback error: %s", err, exc_info=True)

    async def _send_notification(self, item_id: str, item: dict) -> None:
        """Send notification with action buttons."""
        try:
            device_id = item.get("notify_device")
            if not device_id:
                return

            if device_id.startswith("notify."):
                service_target = device_id.split(".", 1)[1]
            elif device_id.startswith("mobile_app_"):
                service_target = device_id
            else:
                service_target = f"mobile_app_{device_id}"

            message = item.get("message") or f"It's {dt_util.now().strftime('%I:%M %p')}"
            payload = {
                "message": message,
                "title": item.get("name", "Alarm & Reminder"),
                "data": {
                    "tag": item_id,
                    "actions": [
                        {"action": "stop", "title": "Stop"},
                        {"action": "snooze", "title": "Snooze"}
                    ]
                }
            }

            _LOGGER.debug("Notify %s -> %s", service_target, payload)
            await self.hass.services.async_call("notify", service_target, payload, blocking=True)

        except Exception as err:
            _LOGGER.error("Error sending notification: %s", err, exc_info=True)

    @callback
    def _on_mobile_notification_action(self, event) -> None:
        """Handle mobile app notification actions."""
        try:
            tag = event.data.get("tag")
            action = event.data.get("action")
            if not tag:
                return

            item_id = tag if tag in self._active_items else self._notification_tag_map.get(tag)
            if not item_id:
                return

            if action == "stop":
                self.hass.async_create_task(
                    self.stop_item(item_id)
                )
            elif action == "snooze":
                self.hass.async_create_task(
                    self.snooze_item(
                        item_id,
                        DEFAULT_SNOOZE_MINUTES,
                    )
                )

        except Exception as err:
            _LOGGER.error("Error handling notification action: %s", err, exc_info=True)

    async def stop_item(self, item_id: str) -> None:
        """Stop an active or scheduled item.
        
        For 'once' items: mark as stopped, ready to be re-enabled later.
        For repeated items: reschedule to next occurrence.
        """
        try:
            if item_id.startswith(f"{DOMAIN}."):
                item_id = item_id.split(".")[-1]

            if item_id not in self._active_items:
                _LOGGER.warning("Item %s not found", item_id)
                return

            item = self._active_items[item_id]
            repeat = item.get("repeat", "once")

            # Set stop event
            if item_id in self._stop_events:
                self._stop_events[item_id].set()

            # Cancel trigger
            if item_id in self._trigger_cancel_funcs:
                try:
                    self._trigger_cancel_funcs[item_id]()
                except Exception:
                    pass
                del self._trigger_cancel_funcs[item_id]

            # Update status
            item["status"] = "stopped"
            item["last_stopped"] = dt_util.now().isoformat()
            
            # For 'once' items, calculate next trigger for when user re-enables
            # For repeated items, reschedule to next occurrence
            if repeat != "once":
                next_trigger = self._calculate_next_trigger(item)
                if next_trigger:
                    item["scheduled_time"] = next_trigger
                    _LOGGER.debug("Stopped recurring item %s, next trigger: %s", item_id, next_trigger)
            
            self._active_items[item_id] = item
            await self.storage.async_save(self._active_items)

            self._update_dashboard_state()
            async_dispatcher_send(self.hass, DASHBOARD_UPDATED)
            async_dispatcher_send(self.hass, ITEM_UPDATED, item_id, item)

            _LOGGER.info("Stopped item: %s", item_id)

        except Exception as err:
            _LOGGER.error("Error stopping item: %s", err, exc_info=True)

    async def snooze_item(self, item_id: str, minutes: int) -> None:
        """Snooze an active item."""
        try:
            if item_id.startswith(f"{DOMAIN}."):
                item_id = item_id.split(".")[-1]

            if item_id not in self._active_items:
                _LOGGER.warning("Item %s not found", item_id)
                return

            item = self._active_items[item_id]

            # Stop current playback
            await self.stop_item(item_id)
            await asyncio.sleep(1)

            # Calculate new time
            now = dt_util.now()
            new_time = now + timedelta(minutes=minutes)
            new_time = new_time.replace(second=0, microsecond=0)

            # Update item
            item = self._active_items[item_id]
            item["scheduled_time"] = new_time
            item["status"] = "scheduled"
            if "last_stopped" in item:
                item["last_rescheduled_from"] = item["last_stopped"]
            item["last_stopped"] = now.isoformat()
            
            # Save to storage
            self._active_items[item_id] = item
            await self.storage.async_save(self._active_items)

            # Schedule new trigger
            self._schedule_item(item_id, new_time)

            self._update_dashboard_state()
            async_dispatcher_send(self.hass, DASHBOARD_UPDATED)
            async_dispatcher_send(self.hass, ITEM_UPDATED, item_id, item)

            _LOGGER.info(
                "Snoozed %s for %d minutes. Will ring at %s",
                item_id,
                minutes,
                new_time.strftime("%H:%M:%S")
            )

        except Exception as err:
            _LOGGER.error("Error snoozing item: %s", err, exc_info=True)

    async def stop_all_items(self, is_alarm: bool = None) -> None:
        """Stop all active items."""
        try:
            stopped_count = 0
            for item_id, item in list(self._active_items.items()):
                if is_alarm is None or item["is_alarm"] == is_alarm:
                    if item["status"] in ["active", "scheduled"]:
                        if item_id in self._stop_events:
                            self._stop_events[item_id].set()
                            await asyncio.sleep(0.1)
                            self._stop_events.pop(item_id, None)
                        
                        if item_id in self._trigger_cancel_funcs:
                            try:
                                self._trigger_cancel_funcs[item_id]()
                            except Exception:
                                pass
                            del self._trigger_cancel_funcs[item_id]
                        
                        item["status"] = "stopped"
                        self._active_items[item_id] = item
                        stopped_count += 1

            if stopped_count > 0:
                await self.storage.async_save(self._active_items)
                self._update_dashboard_state()
                async_dispatcher_send(self.hass, DASHBOARD_UPDATED)
                _LOGGER.info("Successfully stopped %d items", stopped_count)

        except Exception as err:
            _LOGGER.error("Error stopping all items: %s", err, exc_info=True)

    async def edit_item(self, item_id: str, changes: dict) -> None:
        """Edit an existing item."""
        try:
            if item_id.startswith(f"{DOMAIN}."):
                item_id = item_id.split(".")[-1]

            if item_id not in self._active_items:
                _LOGGER.warning("Item %s not found", item_id)
                return

            item = self._active_items[item_id]

            # Update time if provided
            if "time" in changes:
                time_input = changes["time"]
                if isinstance(time_input, str):
                    hour, minute = map(int, time_input.split(':'))
                    from datetime import time as dt_time
                    time_input = dt_time(hour, minute)
                
                current_date = changes.get("date", item["scheduled_time"].date())
                new_time = datetime.combine(current_date, time_input)
                new_time = dt_util.as_local(new_time)
                
                if new_time < dt_util.now() and "date" not in changes:
                    new_time = new_time + timedelta(days=1)
                
                item["scheduled_time"] = new_time
                changes.pop("time", None)
                changes.pop("date", None)

            # Update other fields
            item.update(changes)

            self._active_items[item_id] = item
            await self.storage.async_save(self._active_items)

            # Reschedule if time changed and enabled
            if "scheduled_time" in changes and item.get("enabled", True):
                self._schedule_item(item_id, item["scheduled_time"])

            self._update_dashboard_state()
            async_dispatcher_send(self.hass, DASHBOARD_UPDATED)
            async_dispatcher_send(self.hass, ITEM_UPDATED, item_id, item)

            _LOGGER.info("Edited item: %s", item_id)

        except Exception as err:
            _LOGGER.error("Error editing item: %s", err, exc_info=True)

    async def delete_item(self, item_id: str) -> None:
        """Delete a specific item and remove from entity registry."""
        try:
            # Remove domain prefix if present
            if item_id.startswith(f"{DOMAIN}."):
                item_id = item_id.split(".")[-1]

            if item_id not in self._active_items:
                _LOGGER.warning("Item %s not found", item_id)
                return

            # Stop if active
            if item_id in self._stop_events:
                self._stop_events[item_id].set()
                await asyncio.sleep(0.1)
                self._stop_events.pop(item_id, None)

            # Cancel trigger
            if item_id in self._trigger_cancel_funcs:
                try:
                    self._trigger_cancel_funcs[item_id]()
                except Exception:
                    pass
                del self._trigger_cancel_funcs[item_id]

            # Remove from entity registry immediately
            entity_registry = get_entity_registry(self.hass)
            entity_id = f"switch.{item_id}"
            try:
                entity_registry.async_remove(entity_id)
                _LOGGER.debug("Removed entity %s from registry", entity_id)
            except Exception as err:
                _LOGGER.debug("Entity %s not in registry or already removed: %s", entity_id, err)

            # Delete from storage and memory
            await self.storage.async_delete(item_id)
            self._active_items.pop(item_id)

            # Dispatch event for switch platform
            async_dispatcher_send(self.hass, ITEM_DELETED, item_id)

            self._update_dashboard_state()
            async_dispatcher_send(self.hass, DASHBOARD_UPDATED)

            _LOGGER.info("Deleted item: %s", item_id)

        except Exception as err:
            _LOGGER.error("Error deleting item: %s", err, exc_info=True)

    async def delete_all_items(self, is_alarm: bool = None) -> None:
        """Delete all items."""
        try:
            deleted_count = 0
            entity_registry = get_entity_registry(self.hass)
            
            for item_id in list(self._active_items.keys()):
                item = self._active_items[item_id]
                if is_alarm is None or item["is_alarm"] == is_alarm:
                    # Stop if active
                    if item_id in self._stop_events:
                        self._stop_events[item_id].set()
                        await asyncio.sleep(0.1)
                        self._stop_events.pop(item_id, None)

                    # Cancel trigger
                    if item_id in self._trigger_cancel_funcs:
                        try:
                            self._trigger_cancel_funcs[item_id]()
                        except Exception:
                            pass
                        del self._trigger_cancel_funcs[item_id]

                    # Remove from entity registry
                    entity_id = f"switch.{item_id}"
                    try:
                        entity_registry.async_remove(entity_id)
                        _LOGGER.debug("Removed entity %s from registry", entity_id)
                    except Exception as err:
                        _LOGGER.debug("Entity %s not in registry: %s", entity_id, err)

                    # Delete from storage and memory
                    await self.storage.async_delete(item_id)
                    self._active_items.pop(item_id)
                    
                    # Dispatch event so switch platform can remove entity from registry
                    async_dispatcher_send(self.hass, ITEM_DELETED, item_id)
                    deleted_count += 1

            if deleted_count > 0:
                self._update_dashboard_state()
                async_dispatcher_send(self.hass, DASHBOARD_UPDATED)
                _LOGGER.info("Deleted %d items", deleted_count)

        except Exception as err:
            _LOGGER.error("Error deleting all items: %s", err, exc_info=True)

    def _update_dashboard_state(self) -> None:
        """Update central dashboard entity."""
        try:
            alarms = {}
            reminders = {}
            overall_state = "idle"
            
            for iid, item in self._active_items.items():
                summary = {
                    "name": item.get("name"),
                    "status": item.get("status"),
                    "scheduled_time": (
                        item.get("scheduled_time").isoformat()
                        if isinstance(item.get("scheduled_time"), datetime)
                        else item.get("scheduled_time")
                    ),
                    "message": item.get("message"),
                    "is_alarm": bool(item.get("is_alarm")),
                    "sound_file": item.get("sound_file"),
                    "enabled": item.get("enabled", True),
                }
                
                if item.get("status") == "active":
                    overall_state = "active"
                
                if item.get("is_alarm"):
                    alarms[iid] = summary
                else:
                    reminders[iid] = summary

            attrs = {
                "alarms": alarms,
                "reminders": reminders,
                "alarm_count": len(alarms),
                "reminder_count": len(reminders),
                "last_updated": dt_util.now().isoformat(),
            }
            
            self.hass.states.async_set(f"{DOMAIN}.items", overall_state, attrs)

        except Exception as err:
            _LOGGER.error("Failed to update dashboard state: %s", err, exc_info=True)

def _resolve_sound_file(self, ringtone: str = None, sound_file: str = None, is_alarm: bool = False) -> str:
    """Resolve sound file path from ringtone name or custom file.
    
    Returns the full web URL for the audio file.
    Priority:
    1. If sound_file is provided and not empty, use it (custom file)
    2. If ringtone is provided, resolve to built-in URL
    3. Use default based on alarm/reminder type
    """
    # If custom sound file is provided and not empty, use it
    if sound_file and sound_file.strip():
        _LOGGER.debug("Using custom sound file: %s", sound_file)
        normalized_sound_file = self._normalize_sound_path(sound_file)
        return normalized_sound_file
    
    # Get the base URL (e.g., http://localhost:8123)
    base_url = get_url(self.hass, allow_external=False) or "http://localhost:8123"
    
    # Built-in ringtone URLs (relative to /local/)
    builtin_reminders = {
        "ringtone": "alarm&reminder_sounds/reminders/ringtone.mp3",
        "ringtone_2": "alarm&reminder_sounds/reminders/ringtone_2.mp3",
    }
    
    builtin_alarms = {
        "birds": "alarm&reminder_sounds/alarms/birds.mp3",
    }
    
    # Resolve built-in ringtone
    builtin_map = builtin_alarms if is_alarm else builtin_reminders
    if ringtone and ringtone in builtin_map:
        relative_path = builtin_map[ringtone]
        full_url = f"{base_url}/local/{relative_path}"
        _LOGGER.debug("Using built-in %s URL: %s", "alarm" if is_alarm else "reminder", full_url)
        return full_url
    
    # Fall back to default
    default_relative = builtin_alarms.get("birds") if is_alarm else builtin_reminders.get("ringtone")
    default_url = f"{base_url}/local/{default_relative}"
    _LOGGER.debug("Using default sound file URL: %s", default_url)
    return default_url

def _normalize_sound_path(self, path: str) -> str:
    """Normalize a sound file path to a full URL accessible by satellites.
    
    Handles:
    - Full HTTP/HTTPS URLs (return as-is)
    - /local/ paths (convert to full URL)
    - media-source:// paths (return as-is)
    - Relative paths (convert to /local/ URL)
    
    Args:
        path: The sound file path to normalize
        
    Returns:
        Full URL or media-source URI
    """
    if not path:
        return ""
    
    path = path.strip()
    
    # Already a full URL or media-source
    if path.startswith(("http://", "https://", "media-source://")):
        return path
    
    # Get base URL
    base_url = get_url(self.hass, allow_external=False) or "http://localhost:8123"
    
    # Handle /local/ paths
    if path.startswith("/local/"):
        return f"{base_url}{path}"
    
    # Handle www/ paths (convert to /local/)
    if path.startswith("www/"):
        return f"{base_url}/local/{path[4:]}"
    
    # Handle relative paths (assume they're in www/)
    if not path.startswith("/"):
        return f"{base_url}/local/{path}"
    
    # Default: treat as absolute path from HA root
    return f"{base_url}{path}"
