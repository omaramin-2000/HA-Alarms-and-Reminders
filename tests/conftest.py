"""Common fixtures for testing."""
import os
import pytest
from unittest.mock import patch

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(hass):
    """Enable custom integrations in Home Assistant."""
    hass.data["custom_components"] = {"alarms_and_reminders": {}}
    await hass.async_start()
    yield