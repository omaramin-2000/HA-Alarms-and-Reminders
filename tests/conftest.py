"""Common fixtures for testing."""
import os
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(hass):
    """Enable custom integrations in Home Assistant."""
    hass.config.components.add("alarms_and_reminders")
    await hass.async_start()
    yield