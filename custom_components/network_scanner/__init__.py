"""Network Scanner integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .scanner import NetworkScannerClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]
SCAN_INTERVAL = timedelta(minutes=15)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Network Scanner component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Network Scanner from a config entry."""
    ip_range = config_entry.data.get("ip_range")

    # Collect all mac_mapping_* entries from config
    mac_mappings_list = []
    for i in range(25):
        key = f"mac_mapping_{i+1}"
        mac_mappings_list.append(config_entry.data.get(key, ""))

    i = 25
    while True:
        key = f"mac_mapping_{i+1}"
        if key in config_entry.data:
            mac_mappings_list.append(config_entry.data.get(key))
            i += 1
        else:
            break

    mac_mappings = "\n".join(mac_mappings_list)

    # Build the blocking scanner client in the executor — its constructor
    # calls `nmap --version` synchronously, which must not run on the event loop.
    client = await hass.async_add_executor_job(
        NetworkScannerClient, ip_range, mac_mappings
    )

    async def _async_update_data():
        """Run the blocking nmap scan off the event loop."""
        try:
            return await hass.async_add_executor_job(client.scan)
        except Exception as err:
            raise UpdateFailed(f"Network scan failed: {err}") from err

    coordinator: DataUpdateCoordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{ip_range}",
        update_interval=SCAN_INTERVAL,
        update_method=_async_update_data,
    )

    # IMPORTANT: do NOT await the first refresh here, and do NOT attach the
    # background task to the config entry. Either of those will make HA
    # consider setup as still running until the scan finishes, which triggers
    # "Setup of sensor platform network_scanner is taking over 10 seconds".
    # We fire-and-forget on hass instead, so setup returns immediately.
    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    hass.async_create_background_task(
        coordinator.async_refresh(),
        name=f"{DOMAIN}_initial_refresh",
    )

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id, None)
    return unload_ok
