"""Intent handling for Alarms and Reminders."""
from datetime import datetime
from typing import List
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.translation import async_get_translations

from .const import (
    DOMAIN,
    SERVICE_SET_ALARM,
    SERVICE_SET_REMINDER,
    SERVICE_STOP_ALARM,
    SERVICE_STOP_REMINDER,
    SERVICE_SNOOZE_ALARM,
    SERVICE_SNOOZE_REMINDER,
    DEFAULT_SNOOZE_MINUTES,
)

async def async_setup_intents(hass: HomeAssistant) -> None:
    """Set up the Alarms and Reminders intents."""
    intent.async_register(hass, SetAlarmIntentHandler())
    intent.async_register(hass, SetReminderIntentHandler())
    intent.async_register(hass, StopAlarmIntentHandler())
    intent.async_register(hass, StopReminderIntentHandler())
    intent.async_register(hass, SnoozeAlarmIntentHandler())
    intent.async_register(hass, SnoozeReminderIntentHandler())

class SetAlarmIntentHandler(intent.IntentHandler):
    """Handle SetAlarm intents."""

    intent_type = "SetAlarm"
    slot_schema = {
        vol.Required("datetime"): str,
        vol.Optional("message"): str,
    }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        
        datetime_str = slots["datetime"]["value"]
        message = slots.get("message", {}).get("value")
        satellite = intent_obj.context.id  # Get the satellite that received the command

        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_ALARM,
            {
                "datetime": datetime_str,
                "satellite": satellite,
                "message": message
            },
        )

        speech = f"Alarm set for {datetime_str}"
        if message:
            speech += f" with message: {message}"

        response = intent_obj.create_response()
        response.async_set_speech(speech)
        return response

class SetReminderIntentHandler(intent.IntentHandler):
    """Handle SetReminder intents."""

    intent_type = "SetReminder"
    slot_schema = {
        vol.Required("task"): str,
        vol.Required("datetime"): str,
    }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        
        task = slots["task"]["value"]
        datetime_str = slots["datetime"]["value"]
        satellite = intent_obj.context.id

        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_REMINDER,
            {
                "datetime": datetime_str,
                "satellite": satellite,
                "message": task
            },
        )

        response = intent_obj.create_response()
        response.async_set_speech(f"Reminder set for {datetime_str}: {task}")
        return response

class StopAlarmIntentHandler(intent.IntentHandler):
    """Handle StopAlarm intents."""

    intent_type = "StopAlarm"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        satellite = intent_obj.context.id
        
        # Get coordinator from data
        coordinator = next(iter(hass.data[DOMAIN].values()))
        await coordinator.stop_current_alarm()

        response = intent_obj.create_response()
        response.async_set_speech("Alarm stopped")
        return response

class StopReminderIntentHandler(intent.IntentHandler):
    """Handle StopReminder intents."""

    intent_type = "StopReminder"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        satellite = intent_obj.context.id
        
        coordinator = next(iter(hass.data[DOMAIN].values()))
        await coordinator.stop_current_reminder()

        response = intent_obj.create_response()
        response.async_set_speech("Reminder stopped")
        return response

class SnoozeAlarmIntentHandler(intent.IntentHandler):
    """Handle SnoozeAlarm intents."""

    intent_type = "SnoozeAlarm"
    slot_schema = {
        vol.Optional("minutes"): vol.Coerce(int),
    }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        
        minutes = slots.get("minutes", {}).get("value", DEFAULT_SNOOZE_MINUTES)
        satellite = intent_obj.context.id
        
        coordinator = next(iter(hass.data[DOMAIN].values()))
        await coordinator.snooze_current_alarm(minutes)

        response = intent_obj.create_response()
        response.async_set_speech(f"Alarm snoozed for {minutes} minutes")
        return response

class SnoozeReminderIntentHandler(intent.IntentHandler):
    """Handle SnoozeReminder intents."""

    intent_type = "SnoozeReminder"
    slot_schema = {
        vol.Optional("minutes"): vol.Coerce(int),
    }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        
        minutes = slots.get("minutes", {}).get("value", DEFAULT_SNOOZE_MINUTES)
        satellite = intent_obj.context.id
        
        coordinator = next(iter(hass.data[DOMAIN].values()))
        await coordinator.snooze_current_reminder(minutes)

        response = intent_obj.create_response()
        response.async_set_speech(f"Reminder snoozed for {minutes} minutes")
        return response