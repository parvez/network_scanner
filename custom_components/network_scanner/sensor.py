from __future__ import annotations
import json
import logging
from typing import Any, Dict, List, Optional

import nmap
from aiohttp import ClientError
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, STATUS_SCANNING, STATUS_OK, STATUS_ERROR

_LOGGER = logging.getLogger(__name__)

def _norm_mac(mac: Optional[str]) -> str:
    return (mac or "").upper()

def _parse_dir_obj(obj: Any) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    if not isinstance(obj, dict):
        return out
    block = obj.get("data", obj)
    if not isinstance(block, dict):
        return out
    for k, v in block.items():
        mk = _norm_mac(k)
        if not mk:
            continue
        if isinstance(v, dict):
            out[mk] = {"name": str(v.get("name", "")), "desc": str(v.get("desc", ""))}
        else:
            out[mk] = {"name": str(v), "desc": ""}
    return out

class NetworkScannerExtended(SensorEntity):
    _attr_name = "Network Scanner Extended"
    _attr_native_unit_of_measurement = "Devices"
    _attr_should_poll = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.ip_range: str = entry.options.get("ip_range", entry.data.get("ip_range", ""))
        self._state: Optional[int] = None
        self._devices: List[Dict[str, Any]] = []
        self._status: str = STATUS_OK
        self.nm = nmap.PortScanner()

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self.ip_range}"

    @property
    def native_value(self) -> Optional[int]:
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "status": self._status,
            "ip_range": self.ip_range,
            "devices": self._devices,
        }

    async def async_update(self) -> None:
        # Build effective directory (entry.data base + options text/url)
        try:
            self._status = STATUS_SCANNING
            directory: Dict[str, Dict[str, str]] = dict(self.entry.data.get("mac_directory", {}))

            opts = self.entry.options or {}
            # JSON text in options (highest precedence)
            jtxt = (opts.get("mac_directory_json_text") or "").strip()
            if jtxt:
                try:
                    directory.update(_parse_dir_obj(json.loads(jtxt)))
                except Exception as exc:
                    _LOGGER.warning("Invalid options JSON: %s", exc)

            # Optional URL
            url = (opts.get("mac_directory_json_url") or self.entry.data.get("mac_directory_json_url") or "").strip()
            if url:
                try:
                    session = async_get_clientsession(self.hass)
                    async with session.get(url, timeout=10) as resp:
                        resp.raise_for_status()
                        directory.update(_parse_dir_obj(json.loads(await resp.text())))
                except (ClientError, Exception) as exc:
                    _LOGGER.warning("Failed to fetch directory URL %s: %s", url, exc)

            # Scan (blocking) in executor
            devices = await self.hass.async_add_executor_job(self._scan_network, directory)
            self._devices = devices
            self._state = len(devices)
            self._status = STATUS_OK
        except Exception as exc:
            self._status = STATUS_ERROR
            _LOGGER.error("Network scan failed: %s", exc)

    def _scan_network(self, directory: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
        self.nm.scan(hosts=self.ip_range, arguments="-sn")
        devices: List[Dict[str, Any]] = []
        for host in self.nm.all_hosts():
            try:
                node = self.nm[host]
                addrs = node.get("addresses", {})
                mac = addrs.get("mac")
                ip = addrs.get("ipv4") or addrs.get("ipv6") or ""
                if not mac or not ip:
                    continue

                vendor = "Unknown"
                ven_map = node.get("vendor", {})
                if isinstance(ven_map, dict):
                    for k, v in ven_map.items():
                        if _norm_mac(k) == _norm_mac(mac):
                            vendor = v
                            break

                hostname = node.hostname() or ""
                override = directory.get(_norm_mac(mac), {})
                name = override.get("name") or "Unknown Device"
                desc = override.get("desc") or "Unknown Device"

                devices.append({
                    "ip": ip,
                    "mac": mac,
                    "name": name,
                    "type": desc,
                    "vendor": vendor,
                    "hostname": hostname,
                })
            except Exception as exc:
                _LOGGER.debug("Skipping host %s: %s", host, exc)

        def _ip_key(ip_str: str) -> List[int]:
            try:
                return [int(p) for p in ip_str.split(".")]
            except Exception:
                return [999, 999, 999, 999]

        devices.sort(key=lambda d: _ip_key(d.get("ip", "")))
        return devices

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    ip_range = entry.options.get("ip_range", entry.data.get("ip_range"))
    if not ip_range:
        _LOGGER.error("network_scanner: ip_range missing; not creating entity")
        return
    async_add_entities([NetworkScannerExtended(hass, entry)], False)
