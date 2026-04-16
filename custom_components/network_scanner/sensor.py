"""Network Scanner sensor entity, backed by a DataUpdateCoordinator."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Network Scanner sensor from a config entry."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    ip_range = config_entry.data.get("ip_range")
    async_add_entities([NetworkScannerSensor(coordinator, ip_range)])


class NetworkScannerSensor(CoordinatorEntity, object):
    """Sensor exposing the network scan results.

    The scan itself is owned by the DataUpdateCoordinator. This entity is
    purely a read-only view: no async_update, no blocking work, no warnings
    about long updates.
    """

    _attr_name = "Network Scanner"
    _attr_icon = "mdi:lan"
    _attr_native_unit_of_measurement = "Devices"

    def __init__(self, coordinator: DataUpdateCoordinator, ip_range: str) -> None:
        super().__init__(coordinator)
        self._ip_range = ip_range
        self._attr_unique_id = f"network_scanner_{ip_range}"

    @property
    def native_value(self) -> int | None:
        """Number of devices found in the most recent scan."""
        if self.coordinator.data is None:
            return None
        return len(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict:
        """Expose the full device list as an attribute, like the original sensor."""
        return {"devices": self.coordinator.data or []}
