"""Base HTMLCardStore class."""

from __future__ import annotations

from homeassistant.core import HomeAssistant


class HTMLCardStore:
    hass: HomeAssistant | None = None
    sidepanel_icon: str = "mdi:store"
    sidepanel_title: str = "HTML Card Store"

    def __init__(self) -> None:
        """Initialize."""
        import logging
        self.logger = logging.getLogger(__name__)
