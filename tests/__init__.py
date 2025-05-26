"""Test setup of the Alarms and Reminders integration."""
from unittest.mock import patch
import pytest

from homeassistant.setup import async_setup_component
from custom_components.alarms_and_reminders.const import DOMAIN

@pytest.mark.asyncio
async def test_async_setup(hass):
    """Test the integration setup."""
    with patch("custom_components.alarms_and_reminders.coordinator.AlarmAndReminderCoordinator"):
        # Configure minimal config
        config = {
            DOMAIN: {}
        }
        
        # Test the setup
        assert await async_setup_component(hass, DOMAIN, config)
        await hass.async_block_till_done()

        # Verify domain is in hass.data
        assert DOMAIN in hass.data

        # Verify services are registered
        services = hass.services.async_services().get(DOMAIN)
        assert services is not None
        assert "set_alarm" in services
        assert "set_reminder" in services