from homeassistant.helpers.entity import Entity

class AlarmReminderEntity(Entity):
    """Representation of an Alarm or Reminder."""

    def __init__(self, hass, item_id, data):
        """Initialize the entity."""
        self.hass = hass
        self.item_id = item_id
        self.data = data
        self._attr_name = data.get("name", item_id)
        self._attr_unique_id = item_id

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
