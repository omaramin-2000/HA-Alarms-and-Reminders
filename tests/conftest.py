"""Common fixtures for testing."""
import os
import pytest
from unittest.mock import patch

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(hass):
    """Enable custom integrations in Home Assistant."""
    # Register your component's domain in hass.data
    hass.data["custom_components"] = {
        "alarms_and_reminders": {
            "name": "Alarms and Reminders",
            "domain": "alarms_and_reminders",
        }
    }

    # Add component to config
    hass.config.components.add("alarms_and_reminders")

    await hass.async_start()
    yield