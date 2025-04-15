"""Entity definitions for Alarms and Reminders."""
import voluptuous as vol  
from homeassistant.helpers.entity import Entity
from homeassistant.const import ATTR_NAME
from homeassistant.helpers import entity_platform
from .const import DOMAIN

class AlarmReminderEntity(Entity):
    """Representation of an Alarm or Reminder."""

    def __init__(self, hass, item_id, data):
        """Initialize the entity."""
        self.hass = hass
        self.item_id = item_id
        self.data = data
        self._attr_name = data.get("name", item_id)
        self._attr_unique_id = item_id
        self._attr_should_poll = False
        
    async def async_added_to_hass(self):
        """Run when entity is added to registry."""
        platform = entity_platform.async_get_current_platform()
        
        # Register entity services
        platform.async_register_entity_service(
            "stop",
            {},
            "async_stop"
        )
        
        platform.async_register_entity_service(
            "snooze",
            {
                vol.Optional("minutes", default=5): int,
            },
            "async_snooze"
        )

    async def async_stop(self):
        """Stop the alarm/reminder."""
        if self.data["is_alarm"]:
            await self.hass.services.async_call(
                DOMAIN,
                "stop_alarm",
                {"alarm_id": self.item_id},
                blocking=True
            )
        else:
            await self.hass.services.async_call(
                DOMAIN,
                "stop_reminder",
                {"reminder_id": self.item_id},
                blocking=True
            )

    async def async_snooze(self, minutes: int = 5):
        """Snooze the alarm/reminder."""
        if self.data["is_alarm"]:
            await self.hass.services.async_call(
                DOMAIN,
                "snooze_alarm",
                {
                    "alarm_id": self.item_id,
                    "minutes": minutes
                },
                blocking=True
            )
        else:
            await self.hass.services.async_call(
                DOMAIN,
                "snooze_reminder",
                {
                    "reminder_id": self.item_id,
                    "minutes": minutes
                },
                blocking=True
            )

    async def async_delete(self):
        """Delete the alarm/reminder."""
        coordinator = self.hass.data[DOMAIN].get(next(iter(self.hass.data[DOMAIN])))
        if coordinator:
            await coordinator.delete_item(self.item_id)

    @property
    def name(self):
        """Return the name of the entity."""
        return self._attr_name

    @property
    def state(self):
        """Return the state of the entity."""
        return self.data["status"]

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        attrs = {
            "scheduled_time": self.data["scheduled_time"].isoformat(),
            "message": self.data["message"],
            "repeat": self.data["repeat"],
            "status": self.data["status"],
            "satellite": self.data["satellite"],
            "media_players": self.data.get("media_players", []),
            "is_alarm": self.data["is_alarm"],
            "name": self.data["name"],
            "control_buttons": [
                {
                    "service": f"{DOMAIN}.stop",
                    "name": "Stop",
                    "icon": "mdi:stop"
                },
                {
                    "service": f"{DOMAIN}.snooze",
                    "name": "Snooze",
                    "icon": "mdi:snooze"
                }
            ]
        }
        return attrs

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        if self.data["is_alarm"]:
            return "mdi:alarm-bell" if self.data["status"] == "active" else "mdi:alarm"
        return "mdi:reminder"