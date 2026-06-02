"""Static path registrations for HTML Card Store (unused, kept for reference)."""
from __future__ import annotations

from homeassistant.core import HomeAssistant


async def async_register_frontend(hass: HomeAssistant, _store, _version: str) -> None:
    """No-op: html-pro-card is no longer bundled."""
    return