"""Test setup of the Alarms and Reminders integration."""

from unittest.mock import patch
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

# Import constants directly to avoid path issues
DOMAIN = "alarms_and_reminders"

@pytest.mark.asyncio
async def test_async_setup(hass: HomeAssistant) -> None:
    """Test the integration setup."""
    with patch("custom_components.alarms_and_reminders.coordinator.AlarmAndReminderCoordinator"):
        # Attempt to set up your integration
        assert await async_setup_component(hass, DOMAIN, {})

        # After setup, your domain should be in hass.data
        assert DOMAIN in hass.data
        
        # Test that required services are registered
        services = hass.services.async_services().get(DOMAIN)
        assert services is not None
        assert "set_alarm" in services
        assert "set_reminder" in services