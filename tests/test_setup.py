"""Test setup of the Alarms and Reminders integration."""

import pytest
from homeassistant.setup import async_setup_component

@pytest.mark.asyncio
async def test_async_setup(hass):
    """Test the integration setup."""
    # Attempt to set up your integration
    assert await async_setup_component(hass, "alarms_and_reminders", {}) is True

    # After setup, your domain should be in hass.data
    assert "alarms_and_reminders" in hass.data