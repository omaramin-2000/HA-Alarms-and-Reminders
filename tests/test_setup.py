"""Test setup of the Alarms and Reminders integration."""
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.alarms_and_reminders.const import DOMAIN

@pytest.mark.asyncio
async def test_async_setup(hass: HomeAssistant) -> None:
    """Test the integration setup."""
    # Create mocks with async methods
    coordinator_mock = MagicMock()
    coordinator_mock.start = AsyncMock()
    storage_mock = MagicMock()
    
    with patch(
        "custom_components.alarms_and_reminders.coordinator.AlarmAndReminderCoordinator",
        return_value=coordinator_mock
    ), patch(
        "custom_components.alarms_and_reminders.storage.AlarmReminderStorage",
        return_value=storage_mock
    ):
        # Configure minimal config
        config = {
            DOMAIN: {}
        }

        # Test the setup
        assert await async_setup_component(hass, DOMAIN, config)
        await hass.async_block_till_done()

        # Verify domain data structure
        assert DOMAIN in hass.data
        assert isinstance(hass.data[DOMAIN].get("coordinator"), MagicMock)
        
        # Verify coordinator was started
        coordinator_mock.start.assert_called_once()
        
        # Test that services are registered
        services = hass.services.async_services().get(DOMAIN)
        assert services is not None
        assert "set_alarm" in services
        assert "set_reminder" in services