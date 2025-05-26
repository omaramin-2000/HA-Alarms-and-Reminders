"""Test setup of the Alarms and Reminders integration."""

from unittest.mock import patch
import pytest
from homeassistant.setup import async_setup_component
from custom_components.alarms_and_reminders.const import DOMAIN

@pytest.mark.asyncio
async def test_async_setup(hass):
    """Test the integration setup."""
    # Mock the _get_satellites function to return an empty list
    with patch("custom_components.alarms_and_reminders._get_satellites", return_value=[]):
        # Attempt to set up your integration
        assert await async_setup_component(hass, DOMAIN, {}) is True

        # After setup, your domain should be in hass.data
        assert DOMAIN in hass.data
        
        # Test that the coordinator is initialized
        assert "coordinator" in hass.data[DOMAIN]
        
        # Test that required services are registered
        services = hass.services.async_services().get(DOMAIN)
        assert services is not None
        assert "set_alarm" in services
        assert "set_reminder" in services