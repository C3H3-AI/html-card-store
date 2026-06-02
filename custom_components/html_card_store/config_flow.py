"""Configuration flow for HTML Card Store."""
from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import DOMAIN


class HTMLCardStoreFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HTML Card Store."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Simple single-step setup."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="HTML Card Store",
                data={
                    "mode": "new",
                    "dashboard_title": user_input.get("title", "Html Pro卡片商店"),
                    "dashboard_url": user_input.get("url_path", "card-store"),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional("title", default="Html Pro卡片商店"): str,
                vol.Optional("url_path", default="card-store"): str,
            }),
            description_placeholders={},
        )