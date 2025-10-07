from __future__ import annotations
import json
import logging
from ipaddress import ip_network
import voluptuous as vol
from typing import Any, Dict

from homeassistant import config_entries

try:
    from homeassistant.helpers.selector import selector as ha_selector
    def TextSelector():
        return ha_selector({"text": {"multiline": True}})
except Exception:
    def TextSelector():
        return str

from .const import DOMAIN, DEFAULT_IP_RANGE

_LOGGER = logging.getLogger(__name__)

DEFAULT_NMAP_ARGS = "-sn -PE -PS22,80,443 -PA80,443 -PU53 -T4"

def _normalise_mac_key(mac: str) -> str:
    return mac.upper() if isinstance(mac, str) else ""

class NetworkScannerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        yaml_defaults = self.hass.data.get(DOMAIN, {}) or {}
        schema = vol.Schema({
            vol.Required("ip_range", description={"suggested_value": yaml_defaults.get("ip_range", DEFAULT_IP_RANGE)}): str,
            vol.Optional("nmap_args", description={"suggested_value": DEFAULT_NMAP_ARGS}): str,
            vol.Optional("mac_directory_json_text", description={"suggested_value": ""}): TextSelector(),
            vol.Optional("mac_directory_json_url", description={"suggested_value": ""}): str,
        })

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=schema, errors={})

        errors: Dict[str, str] = {}
        ipr = (user_input.get("ip_range") or "").strip()
        try:
            ip_network(ipr, strict=False)
        except Exception:
            errors["ip_range"] = "invalid_ip_range"

        # Light validation of JSON text
        jtxt = (user_input.get("mac_directory_json_text") or "").strip()
        if jtxt:
            try:
                parsed = json.loads(jtxt)
                if not isinstance(parsed, dict):
                    errors["mac_directory_json_text"] = "invalid_json"
            except Exception:
                errors["mac_directory_json_text"] = "invalid_json"

        if errors:
            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

        # Normalise directory now so the sensor can use it directly
        directory = {}
        if jtxt:
            raw = json.loads(jtxt)
            block = raw.get("data", raw) if isinstance(raw, dict) else {}
            if isinstance(block, dict):
                for k, v in block.items():
                    mk = _normalise_mac_key(k)
                    if not mk:
                        continue
                    if isinstance(v, dict):
                        directory[mk] = {"name": str(v.get("name", "")), "desc": str(v.get("desc", ""))}
                    else:
                        directory[mk] = {"name": str(v), "desc": ""}

        data = {
            "ip_range": ipr,
            "mac_directory": directory,
            "mac_directory_json_url": (user_input.get("mac_directory_json_url") or "").strip(),
        }
        return self.async_create_entry(title="Network Scanner Extended", data=data)

    # Options flow mirrors the same fields
    async def async_step_init(self, user_input=None):
        return await self.async_step_user(user_input)

    async def async_step_options(self, user_input=None):
        return await self.async_step_user(user_input)

class NetworkScannerOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        data = self.entry.data or {}
        opts = self.entry.options or {}

        schema = vol.Schema({
            vol.Required("ip_range", description={"suggested_value": opts.get("ip_range", data.get("ip_range", DEFAULT_IP_RANGE))}): str,
            vol.Optional("nmap_args", description={"suggested_value": DEFAULT_NMAP_ARGS}): str,
            vol.Optional("mac_directory_json_text", description={"suggested_value": opts.get("mac_directory_json_text", "")}): TextSelector(),
            vol.Optional("mac_directory_json_url", description={"suggested_value": opts.get("mac_directory_json_url", data.get("mac_directory_json_url",""))}): str,
        })

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=schema, errors={})

        # Validate similarly
        errors = {}
        try:
            ip_network((user_input.get("ip_range") or "").strip(), strict=False)
        except Exception:
            errors["ip_range"] = "invalid_ip_range"

        jtxt = (user_input.get("mac_directory_json_text") or "").strip()
        if jtxt:
            try:
                parsed = json.loads(jtxt)
                block = parsed.get("data", parsed) if isinstance(parsed, dict) else {}
                if not isinstance(block, dict):
                    errors["mac_directory_json_text"] = "invalid_json"
            except Exception:
                errors["mac_directory_json_text"] = "invalid_json"

        if errors:
            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

        return self.async_create_entry(title="", data={
            "ip_range": (user_input.get("ip_range") or "").strip(),
            "mac_directory_json_text": jtxt,
            "mac_directory_json_url": (user_input.get("mac_directory_json_url") or "").strip(),
        })

async def async_get_options_flow(config_entry: config_entries.ConfigEntry):
    return NetworkScannerOptionsFlow(config_entry)
