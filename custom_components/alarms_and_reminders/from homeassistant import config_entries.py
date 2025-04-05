from homeassistant import config_entries
from homeassistant.const import CONF_NAME
import voluptuous as vol
from .const import (
    DOMAIN,
    CONF_ALARM_SOUND,
    CONF_REMINDER_SOUND,
    DEFAULT_ALARM_SOUND,
    DEFAULT_REMINDER_SOUND
)

class AlarmsAndRemindersConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alarms and Reminders."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            return self.async_create_entry(
                title="Alarms and Reminders",
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(CONF_ALARM_SOUND, default=DEFAULT_ALARM_SOUND): str,
                vol.Optional(CONF_REMINDER_SOUND, default=DEFAULT_REMINDER_SOUND): str,
            }),
            errors=errors
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_ALARM_SOUND,
                    default=self.config_entry.options.get(
                        CONF_ALARM_SOUND, DEFAULT_ALARM_SOUND
                    ),
                ): str,
                vol.Optional(
                    CONF_REMINDER_SOUND,
                    default=self.config_entry.options.get(
                        CONF_REMINDER_SOUND, DEFAULT_REMINDER_SOUND
                    ),
                ): str,
            })
        )