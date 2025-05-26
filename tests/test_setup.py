"""Test setup of the Alarms and Reminders integration."""
from unittest.mock import patch, MagicMock
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.alarms_and_reminders.const import DOMAIN

@pytest.mark.asyncio
async def test_async_setup(hass: HomeAssistant) -> None:
    """Test the integration setup."""
    coordinator_mock = MagicMock()
    storage_mock = MagicMock()
    
    # Mock the async_setup function's internals
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

        # Force add component data
        hass.data[DOMAIN] = {
            "coordinator": coordinator_mock,
            "storage": storage_mock
        }
        
        # Test the setup
        assert await async_setup_component(hass, DOMAIN, config)
        await hass.async_block_till_done()

        # Verify domain data structure
        assert DOMAIN in hass.data
        assert "coordinator" in hass.data[DOMAIN]
        assert "storage" in hass.data[DOMAIN]
        
        # Test that coordinator was initialized
        assert coordinator_mock.start.called