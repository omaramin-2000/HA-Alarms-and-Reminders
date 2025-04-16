"""Coordinator for scheduling alarms and reminders."""
import logging
from typing import Dict, Any
import asyncio
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er
from .const import DOMAIN
from .entity import AlarmReminderEntity
from .storage import AlarmReminderStorage

_LOGGER = logging.getLogger(__name__)

__all__ = ["AlarmAndReminderCoordinator"]

class AlarmAndReminderCoordinator:
    """Coordinates scheduling of alarms and reminders."""
    
    def __init__(self, hass: HomeAssistant, media_handler, announcer):
        """Initialize coordinator."""
        self.hass = hass
        self.media_handler = media_handler
        self.announcer = announcer
        self._active_items: Dict[str, Dict[str, Any]] = {}
        self._stop_events: Dict[str, asyncio.Event] = {}
        self.async_add_entities = None
        self._alarm_counter = 0
        self._reminder_counter = 0
        self.storage = AlarmReminderStorage(hass)
        
        # Load existing items from states with better logging
        _LOGGER.debug("Starting to load existing items")
        try:
            for state in hass.states.async_all():
                if state.entity_id.startswith(f"{DOMAIN}."):
                    item_id = state.entity_id.split(".")[-1]
                    _LOGGER.debug("Found entity: %s with state: %s and attributes: %s", 
                                 state.entity_id, state.state, state.attributes)
                    
                    # Convert the scheduled_time back to datetime if it exists
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
                    
                    # Update counters
                    if attributes.get("is_alarm"):
                        counter_num = int(item_id.split("_")[-1]) if item_id.startswith("alarm_") else 0
                        self._alarm_counter = max(self._alarm_counter, counter_num)
                    
                    _LOGGER.debug("Loaded item: %s with attributes: %s", 
                                item_id, self._active_items[item_id])
            
            _LOGGER.debug("Finished loading items. Active items: %s", self._active_items)
        except Exception as err:
            _LOGGER.error("Error loading existing items: %s", err, exc_info=True)
        
        # Ensure domain data structure exists
        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = {}
        
        # Initialize entities list if not exists
        for config_entry in self.hass.config_entries.async_entries(DOMAIN):
            if config_entry.entry_id not in self.hass.data[DOMAIN]:
                self.hass.data[DOMAIN][config_entry.entry_id] = {}
            if "entities" not in self.hass.data[DOMAIN][config_entry.entry_id]:
                self.hass.data[DOMAIN][config_entry.entry_id]["entities"] = []

    async def async_load_items(self) -> None:
        """Load items from storage."""
        self._active_items = await self.storage.async_load()
        _LOGGER.debug("Loaded items from storage: %s", self._active_items)
        
        # Recreate stop events for active items
        for item_id, item in self._active_items.items():
            if item["status"] == "active":
                self._stop_events[item_id] = asyncio.Event()
        
        # Schedule active items
        now = dt_util.now()
        for item_id, item in self._active_items.items():
            if item["status"] == "scheduled":
                delay = (item["scheduled_time"] - now).total_seconds()
                if delay > 0:
                    self.hass.loop.call_later(
                        delay,
                        lambda: self.hass.async_create_task(
                            self._trigger_item(item_id)
                        )
                    )

    async def schedule_item(self, call: ServiceCall, is_alarm: bool, target: dict) -> None:
        """Schedule an alarm or reminder."""
        try:
            _LOGGER.debug("Scheduling %s with data: %s", "alarm" if is_alarm else "reminder", call.data)
            
            # Handle item naming with proper string handling
            provided_name = call.data.get("name", "").strip()  # Add strip() to clean up whitespace
            
            if is_alarm:
                if provided_name:
                    display_name = provided_name
                    # Create entity_id by replacing spaces with underscores
                    entity_id = provided_name.replace(" ", "_").lower()
                    # Ensure unique entity_id by appending number if needed
                    base_id = entity_id
                    counter = 1
                    while f"{entity_id}" in self._active_items:
                        entity_id = f"{base_id}_{counter}"
                        counter += 1
                    item_name = entity_id
                else:
                    # Auto-generate alarm name
                    self._alarm_counter += 1
                    item_name = f"alarm_{self._alarm_counter}"
                    display_name = item_name
            else:
                # For reminders, name is required by schema
                display_name = provided_name
                # Create entity_id by replacing spaces with underscores
                item_name = provided_name.replace(" ", "_").lower()

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
                scheduled_time = datetime.combine(date_input, time_input)
                scheduled_time = dt_util.as_local(scheduled_time)
            else:
                scheduled_time = datetime.combine(now.date(), time_input)
                scheduled_time = dt_util.as_local(scheduled_time)
                if scheduled_time < now:
                    scheduled_time = scheduled_time + timedelta(days=1)

            delay = (scheduled_time - now).total_seconds()
            if delay < 0:
                _LOGGER.warning("Scheduled time %s is in the past. Ignoring request.", scheduled_time)
                return

            # Create entity_id and store item
            entity_id = f"{DOMAIN}.{item_name}"
            
            # Create stop event
            self._stop_events[item_name] = asyncio.Event()
            
            # Create item data with all necessary fields
            item_data = {
                "scheduled_time": scheduled_time,
                "satellite": target.get("satellite"),
                "media_players": target.get("media_players", []),
                "message": message,
                "is_alarm": is_alarm,
                "repeat": repeat,
                "repeat_days": repeat_days,
                "status": "scheduled",
                "name": display_name,
                "entity_id": item_name,
                "unique_id": item_name
            }
            
            # Store in active items and save to storage
            self._active_items[item_name] = item_data
            await self.storage.async_save(self._active_items)
            
            # Create and register entity state with datetime conversion
            state_data = dict(item_data)
            state_data["scheduled_time"] = item_data["scheduled_time"].isoformat()
            self.hass.states.async_set(entity_id, "scheduled", state_data)
            
            # Create entity object
            entity = AlarmReminderEntity(self.hass, item_name, item_data)
            
            # Store in HA registry using the new method
            entity_registry = er.async_get(self.hass)
            entity_registry.async_get_or_create(
                domain=DOMAIN,
                platform="alarms_and_reminders",
                unique_id=item_name,
                suggested_object_id=item_name,
                original_name=display_name
            )

            _LOGGER.debug("Created item %s with data: %s", item_name, item_data)
            _LOGGER.debug("Active items after creation: %s", self._active_items)

            # Schedule the action
            self.hass.loop.call_later(
                delay,
                lambda: self.hass.async_create_task(self._trigger_item(item_name))
            )

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
            stop_event = self._stop_events.get(item_id)

            # Start playback loop
            if item["satellite"]:
                await self._satellite_playback_loop(item, stop_event)
            elif item["media_players"]:
                await self._media_player_playback_loop(item, stop_event)

        except Exception as err:
            _LOGGER.error("Error triggering item %s: %s", item_id, err)
            item["status"] = "error"

    async def _satellite_playback_loop(self, item: dict, stop_event: asyncio.Event) -> None:
        """Handle satellite playback loop."""
        try:
            # Get appropriate sound file
            sound_file = self.media_handler.alarm_sound if item["is_alarm"] else self.media_handler.reminder_sound

            # Use announcer to handle satellite playback
            await self.announcer.announce_on_satellite(
                satellite=item["satellite"],
                message=item["message"],
                sound_file=sound_file,
                stop_event=stop_event,
                name=item["name"],  # Use the generated/provided name
                is_alarm=item["is_alarm"]
            )

        except Exception as err:
            _LOGGER.error("Error in satellite playback loop: %s", err)
            item["status"] = "error"

    async def _media_player_playback_loop(self, item: dict, stop_event: asyncio.Event) -> None:
        """Handle media player playback loop."""
        while not stop_event.is_set():
            try:
                for media_player in item["media_players"]:
                    # Wait for media player to be idle
                    while not await self._is_media_player_idle(media_player):
                        await asyncio.sleep(1)

                    # Format message with current time
                    current_time = self._format_time()
                    message = f"It's {current_time}. {item['message']}" if item['message'] else f"It's {current_time}"

                    # Use media handler to play on media player
                    await self.media_handler.play_on_media_player(
                        media_player,
                        message,
                        item["is_alarm"]
                    )

                # Wait for completion or stop event
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=60)
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
        # Get time format from core config
        time_format = self.hass.config.time_zone.endswith('12h')
        return now.strftime("%I:%M %p") if time_format else now.strftime("%H:%M")

    async def delete_item(self, item_id: str) -> None:
        """Delete an alarm/reminder."""
        if item_id in self._active_items:
            # Stop if active
            if item_id in self._stop_events:
                self._stop_events[item_id].set()
                del self._stop_events[item_id]
            
            # Remove from active items
            del self._active_items[item_id]
            
            # Remove entity
            self.hass.states.async_remove(f"{DOMAIN}.{item_id}")
            
            # Remove from storage
            await self.storage.async_delete_item(item_id)
            
            # Update sensors
            self.hass.bus.async_fire(f"{DOMAIN}_state_changed")

    async def stop_item(self, item_id: str, is_alarm: bool) -> None:
        """Stop an active item."""
        try:
            _LOGGER.debug("Stop request for %s. Current active items: %s", 
                         item_id, 
                         {k: {'name': v.get('name'), 'status': v.get('status')} 
                          for k, v in self._active_items.items()})

            # Remove domain prefix if present
            if item_id.startswith(f"{DOMAIN}."):
                item_id = item_id.split(".")[-1]

            # Try to find the item
            found_id = None
            if item_id in self._active_items:
                found_id = item_id
            else:
                # Try by display name
                display_name = item_id.replace("_", " ")
                for aid, item in self._active_items.items():
                    if (item["name"].lower() == display_name.lower() or 
                        item["entity_id"] == item_id):
                        found_id = aid
                        break

            if found_id:
                item = self._active_items[found_id]
                _LOGGER.debug("Found item to stop: %s", item)
                
                # Remove domain prefix if present
                if item_id.startswith(f"{DOMAIN}."):
                    item_id = item_id.split(".")[-1]

                _LOGGER.debug("Attempting to stop item %s (is_alarm=%s). Active items: %s", 
                            item_id, is_alarm, self._active_items)

                # Try to find the item by ID first
                if item_id in self._active_items:
                    found_id = item_id
                else:
                    # Try to find by display name or entity_id
                    display_name = item_id.replace("_", " ")
                    found_id = next(
                        (aid for aid, item in self._active_items.items()
                        if item["name"].lower() == display_name.lower() or 
                        item["entity_id"] == item_id),
                        None
                    )

                if found_id and found_id in self._active_items:
                    item = self._active_items[found_id]
                    
                    # Check if item type matches
                    if item["is_alarm"] != is_alarm:
                        _LOGGER.warning(
                            "Attempted to stop %s with wrong service: %s", 
                            "alarm" if item["is_alarm"] else "reminder",
                            found_id
                        )
                        return

                    # Stop the item
                    if found_id in self._stop_events:
                        self._stop_events[found_id].set()
                        await asyncio.sleep(0.1)
                        self._stop_events.pop(found_id)
                    
                    # Update item status
                    item["status"] = "stopped"
                    
                    # Update entity state
                    self.hass.states.async_set(
                        f"{DOMAIN}.{found_id}",
                        "stopped",
                        item
                    )

                    # Force update of sensors
                    self.hass.bus.async_fire(f"{DOMAIN}_state_changed")

                    _LOGGER.info(
                        "Successfully stopped %s: %s", 
                        "alarm" if is_alarm else "reminder",
                        found_id
                    )

                else:
                    _LOGGER.warning(
                        "Item %s not found in active items: %s", 
                        item_id, 
                        [f"{k} ({v.get('name', '')}, {v.get('status', '')})" 
                        for k, v in self._active_items.items()]
                    )

        except Exception as err:
            _LOGGER.error("Error stopping item %s: %s", item_id, err, exc_info=True)

    async def snooze_item(self, item_id: str, minutes: int, is_alarm: bool) -> None:
        """Snooze an active item."""
        if item_id in self._active_items:
            await self.media_handler.snooze_alarm(item_id, minutes)
            _LOGGER.info(
                "Successfully snoozed %s for %d minutes: %s", 
                "alarm" if is_alarm else "reminder",
                minutes,
                item_id
            )
        else:
            _LOGGER.warning("Item %s not found in active items: %s", item_id, self._active_items.keys())

    async def stop_all_items(self, is_alarm: bool = None) -> None:
        """Stop all active items. If is_alarm is None, stops both alarms and reminders."""
        try:
            stopped_count = 0
            for item_id, item in list(self._active_items.items()):  # Use list to avoid modification during iteration
                if is_alarm is None or item["is_alarm"] == is_alarm:
                    if item["status"] in ["active", "scheduled"]:
                        # Stop the item
                        if item_id in self._stop_events:
                            self._stop_events[item_id].set()
                            await asyncio.sleep(0.1)
                            self._stop_events.pop(item_id)
                        
                        # Update item status
                        item["status"] = "stopped"
                        self._active_items[item_id] = item
                        
                        # Update entity state
                        self.hass.states.async_set(
                            f"{DOMAIN}.{item_id}",
                            "stopped",
                            item
                        )
                        stopped_count += 1

            if stopped_count > 0:
                # Force update of sensors
                self.hass.bus.async_fire(f"{DOMAIN}_state_changed")
                _LOGGER.info(
                    "Successfully stopped %d %s", 
                    stopped_count,
                    "alarms" if is_alarm else "reminders" if is_alarm is not None else "items"
                )
            else:
                _LOGGER.info("No active items to stop")

        except Exception as err:
            _LOGGER.error("Error stopping all items: %s", err, exc_info=True)

    async def edit_item(self, item_id: str, changes: dict, is_alarm: bool) -> None:
        """Edit an existing alarm or reminder."""
        try:
            _LOGGER.debug("Starting edit request for %s", item_id)
            _LOGGER.debug("Changes requested: %s", changes)
            _LOGGER.debug("Current active items: %s", 
                         {k: {'name': v.get('name'), 'status': v.get('status')} 
                          for k, v in self._active_items.items()})

            # Remove domain prefix if present
            if item_id.startswith(f"{DOMAIN}."):
                item_id = item_id.split(".")[-1]

            # Try to find the item by ID or name
            found_id = None
            if item_id in self._active_items:
                found_id = item_id
            else:
                # Try by name
                name_to_find = item_id.replace("_", " ").lower()
                for aid, item in self._active_items.items():
                    if (item.get('name', '').lower() == name_to_find or 
                        aid.lower() == name_to_find):
                        found_id = aid
                        break

            if not found_id:
                _LOGGER.error("Item %s not found in active items: %s", 
                             item_id,
                             [f"{k} ({v.get('name', '')}, {v.get('status', '')})" 
                              for k, v in self._active_items.items()])
                return

            item = self._active_items[found_id]
            
            # Verify item type matches
            if item.get("is_alarm") != is_alarm:
                _LOGGER.error(
                    "Cannot edit %s as %s", 
                    "alarm" if is_alarm else "reminder",
                    "reminder" if is_alarm else "alarm"
                )
                return

            # Process changes
            if "time" in changes:
                time_input = changes["time"]
                if isinstance(time_input, str):
                    hour, minute = map(int, time_input.split(':'))
                    time_input = datetime.time(hour, minute)
                
                # Get current date or new date if provided
                current_date = (
                    changes["date"] if "date" in changes 
                    else item["scheduled_time"].date()
                )
                
                # Create new scheduled time
                new_time = datetime.combine(current_date, time_input)
                new_time = dt_util.as_local(new_time)
                
                # Check if new time is in the past
                if new_time < dt_util.now():
                    if "date" not in changes:  # Only adjust if date wasn't explicitly set
                        new_time = new_time + timedelta(days=1)
                
                item["scheduled_time"] = new_time

            # Update other fields if provided
            for field in ["name", "message", "satellite", "media_player"]:
                if field in changes:
                    item[field] = changes[field]

            # Store updated item
            self._active_items[found_id] = item
            
            # Save to storage
            await self.storage.async_save(self._active_items)

            # Update entity state
            self.hass.states.async_set(
                f"{DOMAIN}.{found_id}",
                "scheduled",
                item
            )

            # Force update of sensors
            self.hass.bus.async_fire(f"{DOMAIN}_state_changed")

            _LOGGER.info(
                "Successfully edited %s: %s", 
                "alarm" if is_alarm else "reminder",
                found_id
            )

        except Exception as err:
            _LOGGER.error("Error editing item %s: %s", item_id, err, exc_info=True)

    async def delete_item(self, item_id: str, is_alarm: bool) -> None:
        """Delete a specific item."""
        try:
            # Remove domain prefix if present
            if item_id.startswith(f"{DOMAIN}."):
                item_id = item_id.split(".")[-1]

            if item_id not in self._active_items:
                _LOGGER.warning("Item %s not found for deletion", item_id)
                return

            item = self._active_items[item_id]
            
            # Verify item type matches
            if item["is_alarm"] != is_alarm:
                _LOGGER.error(
                    "Cannot delete %s as %s", 
                    "alarm" if is_alarm else "reminder",
                    "reminder" if is_alarm else "alarm"
                )
                return

            # Stop if active
            if item_id in self._stop_events:
                self._stop_events[item_id].set()
                await asyncio.sleep(0.1)
                self._stop_events.pop(item_id)

            # Remove from storage and active items
            await self.storage.async_delete_item(item_id)
            self._active_items.pop(item_id)

            # Remove entity
            self.hass.states.async_remove(f"{DOMAIN}.{item_id}")

            # Force update of sensors
            self.hass.bus.async_fire(f"{DOMAIN}_state_changed")

            _LOGGER.info(
                "Successfully deleted %s: %s",
                "alarm" if is_alarm else "reminder",
                item_id
            )

        except Exception as err:
            _LOGGER.error("Error deleting item %s: %s", item_id, err, exc_info=True)

    async def delete_all_items(self, is_alarm: bool = None) -> None:
        """Delete all items. If is_alarm is None, deletes both alarms and reminders."""
        try:
            deleted_count = 0
            for item_id in list(self._active_items.keys()):
                item = self._active_items[item_id]
                if is_alarm is None or item["is_alarm"] == is_alarm:
                    # Stop if active
                    if item_id in self._stop_events:
                        self._stop_events[item_id].set()
                        await asyncio.sleep(0.1)
                        self._stop_events.pop(item_id)

                    # Remove from storage and active items
                    await self.storage.async_delete_item(item_id)
                    self._active_items.pop(item_id)

                    # Remove entity
                    self.hass.states.async_remove(f"{DOMAIN}.{item_id}")
                    
                    deleted_count += 1

            if deleted_count > 0:
                # Force update of sensors
                self.hass.bus.async_fire(f"{DOMAIN}_state_changed")
                _LOGGER.info(
                    "Successfully deleted %d %s",
                    deleted_count,
                    "alarms" if is_alarm else "reminders" if is_alarm is not None else "items"
                )
            else:
                _LOGGER.info("No items to delete")

        except Exception as err:
            _LOGGER.error("Error deleting all items: %s", err, exc_info=True)
