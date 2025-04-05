"""Config flow for Alarms and Reminders integration."""
from homeassistant import config_entries
import voluptuous as vol

from .const import (
    DOMAIN,
    CONF_ALARM_SOUND,
    CONF_REMINDER_SOUND,
    CONF_MEDIA_PLAYER,
    DEFAULT_ALARM_SOUND,
    DEFAULT_REMINDER_SOUND,
    DEFAULT_MEDIA_PLAYER
)

class AlarmsAndRemindersConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alarms and Reminders."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            # Don't store media_player in initial config
            return self.async_create_entry(
                title="Alarms and Reminders",
                data={
                    CONF_ALARM_SOUND: user_input.get(CONF_ALARM_SOUND, DEFAULT_ALARM_SOUND),
                    CONF_REMINDER_SOUND: user_input.get(CONF_REMINDER_SOUND, DEFAULT_REMINDER_SOUND)
                }
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
            # Convert "none" to None
            if user_input.get(CONF_MEDIA_PLAYER) == "none":
                user_input[CONF_MEDIA_PLAYER] = None
            return self.async_create_entry(title="", data=user_input)

        # Get list of media players plus "none" option
        media_players = ["none"]
        media_player_entities = self.hass.states.async_entity_ids("media_player")
        media_players.extend(media_player_entities)

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
                vol.Optional(
                    CONF_MEDIA_PLAYER,
                    default=self.config_entry.options.get(CONF_MEDIA_PLAYER, "none")
                ): vol.In(media_players),
            })
        )