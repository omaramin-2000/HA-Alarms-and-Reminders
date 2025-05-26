"""Test setup of the Alarms and Reminders integration."""
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alarms_and_reminders.const import DOMAIN

@pytest.mark.skip("Not valid for config-entry-only integrations")
@pytest.mark.asyncio
async def test_async_setup(hass: HomeAssistant) -> None:
    """Test the integration setup."""
    # This test is not valid for config-entry-only integrations.
    pass

@pytest.mark.asyncio
async def test_async_setup_entry(hass: HomeAssistant) -> None:
    """Test the config entry setup."""
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
        entry = MockConfigEntry(domain=DOMAIN, data={})
        entry.add_to_hass(hass)

        from custom_components.alarms_and_reminders import async_setup_entry

        assert await async_setup_entry(hass, entry)
        assert DOMAIN in hass.data
        assert "coordinator" in hass.data[DOMAIN]
        assert "storage" in hass.data[DOMAIN]
        coordinator_mock.start.assert_called_once()