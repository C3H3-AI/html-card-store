"""HTML Card Store Integration for Home Assistant."""
from __future__ import annotations

import os
import logging
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.components.frontend import async_register_built_in_panel, async_remove_panel
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.lovelace import LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import LovelaceStorage

from .const import DOMAIN

__version__ = "1.0"

STORE_VIEW_TITLE = "商店"
_LOGGER = logging.getLogger(__name__)


class StoreDataView(HomeAssistantView):
    url = "/api/html_card_store/user_data"
    name = "api:html_card_store:store_data"
    requires_auth = True

    async def get(self, request):
        hass = request.app["hass"]
        store = Store(hass, 1, "html_card_store.user_data")
        data = await store.async_load()
        return self.json(data or {
            "custom_modules": [],
            "favorites": [],
            "recent": []
        })

    async def post(self, request):
        hass = request.app["hass"]
        data = await request.json()
        store = Store(hass, 1, "html_card_store.user_data")
        await store.async_save(data)
        return self.json({"success": True})


class InstallHPCView(HomeAssistantView):
    url = "/api/html_card_store/install_hpc"
    name = "api:html_card_store:install_hpc"
    requires_auth = True

    async def post(self, request):
        hass = request.app["hass"]
        import os
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        target_dir = "/config/www"
        target_file = os.path.join(target_dir, "html-card-pro.js")
        download_url = "https://raw.githubusercontent.com/ha-china/html-card-pro/main/dist/html-card-pro.js"

        try:
            session = async_get_clientsession(hass)
            async with session.get(download_url) as resp:
                if resp.status != 200:
                    return self.json({"error": f"Download failed: {resp.status}"}, status_code=500)
                content = await resp.read()

            os.makedirs(target_dir, exist_ok=True)
            with open(target_file, "wb") as f:
                f.write(content)

            return self.json({"success": True, "path": "/local/html-card-pro.js"})
        except Exception as e:
            return self.json({"error": str(e)}, status_code=500)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HTML Card Store from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Register custom modules API
    hass.http.register_view(StoreDataView)
    hass.http.register_view(InstallHPCView)

    try:
        await _async_deploy(hass, entry)
    except Exception as ex:
        _LOGGER.exception("Deploy failed: %s", ex)
        return False

    hass.data[DOMAIN] = True
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload HTML Card Store and clean up dashboard + sidebar."""
    hass.data.pop(DOMAIN, None)
    await _async_cleanup(hass, entry)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove entry - final cleanup safety net."""
    await _async_cleanup(hass, entry)


async def _async_cleanup(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Shared cleanup logic for unload and remove."""
    url_path = entry.data["dashboard_url"]
    store_id = url_path.replace("-", "_")

    try:
        if LOVELACE_DATA in hass.data and url_path in hass.data[LOVELACE_DATA].dashboards:
            await hass.data[LOVELACE_DATA].dashboards[url_path].async_delete()
            hass.data[LOVELACE_DATA].dashboards.pop(url_path, None)
            _LOGGER.info("Removed dashboard from hass.data: %s", url_path)
    except Exception as ex:
        _LOGGER.warning("Failed to remove from lovelace data: %s", ex)

    try:
        async_remove_panel(hass, url_path)
        _LOGGER.info("Removed sidebar panel: %s", url_path)
    except Exception as ex:
        _LOGGER.warning("Failed to remove panel: %s", ex)

    try:
        dash_store = Store(hass, 1, "lovelace_dashboards")
        raw = await dash_store.async_load()
        if raw and "items" in raw:
            raw["items"] = [
                d for d in raw["items"]
                if d.get("id") not in (store_id, url_path)
            ]
            await dash_store.async_save(raw)
            _LOGGER.info("Removed dashboard storage entry: %s", store_id)
    except Exception as ex:
        _LOGGER.warning("Failed to remove dashboard entry: %s", ex)

    for key in (f"lovelace.{store_id}", f"lovelace.{url_path}"):
        try:
            store = Store(hass, 1, key)
            await store.async_remove()
            _LOGGER.info("Removed storage: %s", key)
        except Exception as ex:
            _LOGGER.warning("Failed to remove %s: %s", key, ex)


async def _async_deploy(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Deploy store panel."""
    data = entry.data
    url_path = data["dashboard_url"]
    store_id = url_path.replace("-", "_")
    dashboard_title = data.get("dashboard_title", "Html Pro卡片商店")

    www_path = os.path.join(os.path.dirname(__file__), "www")

    target_dir = "/config/www/html_card_store"
    target_file = os.path.join(target_dir, "index.html")
    source_file = os.path.join(www_path, "index.html")

    try:
        os.makedirs(target_dir, exist_ok=True)
        if os.path.isfile(source_file):
            shutil.copy2(source_file, target_file)
            _LOGGER.info("Copied index.html to %s", target_file)
    except Exception as ex:
        _LOGGER.warning("Failed to copy index.html: %s", ex)

    dash_store = Store(hass, 1, "lovelace_dashboards")
    raw = await dash_store.async_load()
    dashboards = raw if raw else {"items": []}
    existing_ids = {d.get("id") for d in dashboards.get("items", [])}

    if store_id not in existing_ids:
        dashboards.setdefault("items", []).append({
            "id": store_id,
            "title": dashboard_title,
            "url_path": url_path,
            "icon": "mdi:store",
            "show_in_sidebar": True,
            "require_admin": False,
            "mode": "storage",
        })
        await dash_store.async_save(dashboards)
        _LOGGER.info("Created dashboard entry: %s", store_id)

    config_store = Store(hass, 1, f"lovelace.{store_id}")
    raw_config = await config_store.async_load()

    config_body = {"views": []}
    if raw_config and isinstance(raw_config, dict):
        if "config" in raw_config:
            existing = raw_config["config"]
        else:
            existing = raw_config
        if existing and isinstance(existing, dict):
            if "strategy" in existing:
                del existing["strategy"]
            config_body = existing

    iframe_url = f"/local/html_card_store/index.html?v={__version__}"
    store_view = {
        "title": STORE_VIEW_TITLE,
        "path": "store",
        "icon": "mdi:store",
        "type": "panel",
        "cards": [{
            "type": "iframe",
            "url": iframe_url,
            "aspect_ratio": "100%",
        }],
    }

    config_body.setdefault("views", [])
    config_body["views"] = [v for v in config_body["views"] if v.get("path") != "store"]
    config_body["views"].insert(0, store_view)
    await config_store.async_save({"config": config_body})

    try:
        async_register_built_in_panel(
            hass,
            component_name="lovelace",
            sidebar_title=dashboard_title,
            sidebar_icon="mdi:store",
            config={"mode": "storage"},
            frontend_url_path=url_path,
            require_admin=False,
            show_in_sidebar=True,
            update=True,
        )
        _LOGGER.info("Registered sidebar panel: %s", url_path)
    except Exception as ex:
        _LOGGER.warning("Panel registration: %s", ex)

    if LOVELACE_DATA in hass.data:
        lovelace_data = hass.data[LOVELACE_DATA]
        if url_path not in lovelace_data.dashboards:
            lovelace_data.dashboards[url_path] = LovelaceStorage(hass, {
                "id": store_id,
                "url_path": url_path,
                "title": dashboard_title,
                "icon": "mdi:store",
                "show_in_sidebar": True,
                "require_admin": False,
            })
            _LOGGER.info("Registered LovelaceStorage for: %s", url_path)