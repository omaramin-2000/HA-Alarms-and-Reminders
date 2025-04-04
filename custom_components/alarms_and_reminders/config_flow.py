# filepath: ha-alarms-and-reminders/custom_components/alarms_and_reminders/config_flow.py

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from .const import DOMAIN

class AlarmsAndRemindersConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alarms and Reminders."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user")

        # Here you can add validation for user_input if needed
        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)