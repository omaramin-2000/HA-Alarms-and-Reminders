from homeassistant.helpers.entity import Entity

class AlarmReminderEntity(Entity):
    """Representation of an Alarm or Reminder."""

    def __init__(self, hass, item_id, data):
        """Initialize the entity."""
        self.hass = hass
        self.item_id = item_id
        self.data = data
        self._attr_name = f"{'Alarm' if data['is_alarm'] else 'Reminder'} {item_id}"
        self._attr_unique_id = item_id

    @property
    def state(self):
        """Return the state of the entity."""
        return self.data["status"]

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        return self.data
