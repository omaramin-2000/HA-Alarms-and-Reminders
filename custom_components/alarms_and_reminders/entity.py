from homeassistant.helpers.entity import Entity
from homeassistant.const import ATTR_NAME
from homeassistant.helpers import entity_platform

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
        
        platform.async_register_entity_service(
            "delete",
            {},
            "async_delete"
        )

    async def async_stop(self):
        """Stop the alarm/reminder."""
        coordinator = self.hass.data[DOMAIN]["coordinator"]
        await coordinator.stop_item(self.item_id, self.data["is_alarm"])

    async def async_snooze(self, minutes: int = 5):
        """Snooze the alarm/reminder."""
        coordinator = self.hass.data[DOMAIN]["coordinator"]
        await coordinator.snooze_item(self.item_id, minutes, self.data["is_alarm"])

    async def async_delete(self):
        """Delete the alarm/reminder."""
        coordinator = self.hass.data[DOMAIN]["coordinator"]
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
        """Return the extra state attributes."""
        return {
            "scheduled_time": self.data["scheduled_time"].isoformat(),
            "message": self.data["message"],
            "repeat": self.data["repeat"],
            "repeat_days": self.data["repeat_days"],
            "status": self.data["status"],
            "satellite": self.data["satellite"],
            "media_players": self.data["media_players"],
            "is_alarm": self.data["is_alarm"]
        }
