"""Config flow for Alarms and Reminders integration."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_ALARM_SOUND,
    CONF_REMINDER_SOUND,
    CONF_MEDIA_PLAYER,
    DEFAULT_ALARM_SOUND,
    DEFAULT_REMINDER_SOUND,
    DEFAULT_MEDIA_PLAYER,
    DEFAULT_NAME
)

@config_entries.HANDLERS.register(DOMAIN)
class AlarmsAndRemindersConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alarms and Reminders."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title=DEFAULT_NAME, data={})

        return self.async_show_form(step_id="user")

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