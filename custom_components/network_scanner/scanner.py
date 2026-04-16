"""Pure nmap scanning logic, isolated from Home Assistant internals.

This module must not import anything from homeassistant, and must not touch
the event loop. All calls into it run inside the executor via the coordinator.
"""
from __future__ import annotations

import logging
import re
import socket
from typing import Any

import nmap

_LOGGER = logging.getLogger(__name__)

# nmap args:
#   -sn                : ping scan only, no port scan
#   -n                 : skip DNS (we do fast reverse-DNS ourselves, only for live IPs)
#   -T4                : aggressive timing template
#   --min-parallelism  : probe many hosts at once
#   --max-retries 1    : don't linger on unresponsive hosts
#   --host-timeout 3s  : give up on any single host after 3s
NMAP_ARGS = "-sn -n -T4 --min-parallelism 64 --max-retries 1 --host-timeout 3s"


class NetworkScannerClient:
    """Blocking nmap client. One instance per config entry."""

    def __init__(self, ip_range: str, mac_mapping: str) -> None:
        self.ip_range = ip_range
        self.mac_mapping = self._parse_mac_mapping(mac_mapping)
        self.nm = nmap.PortScanner()
        _LOGGER.info("Network Scanner client initialized for %s", ip_range)

    # ---------------------- helpers ----------------------
    @staticmethod
    def _parse_mac_mapping(mapping_string: str) -> dict[str, tuple[str, str]]:
        mapping: dict[str, tuple[str, str]] = {}
        for line in mapping_string.split("\n"):
            parts = line.split(";")
            if len(parts) >= 3:
                mapping[parts[0].lower()] = (parts[1], parts[2])
        return mapping

    @staticmethod
    def _short_label(name: str) -> str | None:
        """Return lowercase host label before first dot, cleaned, or None."""
        if not name:
            return None
        short = name.strip().rstrip(".").split(".", 1)[0].lower()
        short = re.sub(r"[^a-z0-9_-]", "", short)
        return short or None

    @staticmethod
    def _fast_rdns(ip: str, timeout: float = 0.3) -> str | None:
        """Reverse-DNS with a very short timeout; returns cleaned short label or None."""
        old_to = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            host, _, _ = socket.gethostbyaddr(ip)
            return NetworkScannerClient._short_label(host)
        except Exception:
            return None
        finally:
            socket.setdefaulttimeout(old_to)

    def _get_device_info_from_mac(self, mac_address: str) -> tuple[str, str]:
        return self.mac_mapping.get(
            mac_address.lower(), ("Unknown Device", "Unknown Device")
        )

    # ---------------------- main entry point ----------------------
    def scan(self) -> list[dict[str, Any]]:
        """Run an nmap ping scan and return the list of discovered devices.

        Blocking. Must be called from the executor, never from the event loop.
        """
        try:
            self.nm.scan(hosts=self.ip_range, arguments=NMAP_ARGS)
        except Exception as err:
            _LOGGER.error("nmap scan failed with args '%s': %s", NMAP_ARGS, err)
            raise

        devices: list[dict[str, Any]] = []

        for host in self.nm.all_hosts():
            try:
                addrs = self.nm[host].get("addresses", {})
                if "mac" not in addrs or "ipv4" not in addrs:
                    continue

                ip = addrs["ipv4"]
                mac = addrs["mac"]

                # Vendor from nmap's OUI db, if known
                vendor = "Unknown"
                vendor_map = self.nm[host].get("vendor", {})
                if mac in vendor_map:
                    vendor = vendor_map[mac]

                # Hostname: try nmap result first (usually empty because -n)
                raw_hostname = self.nm[host].hostname() or ""
                if not raw_hostname:
                    for h in self.nm[host].get("hostnames", []):
                        n = h.get("name")
                        if n:
                            raw_hostname = n
                            break

                hostname = self._short_label(raw_hostname)
                if not hostname:
                    hostname = self._fast_rdns(ip, timeout=0.3)

                device_name, device_type = self._get_device_info_from_mac(mac)
                devices.append(
                    {
                        "ip": ip,
                        "mac": mac,
                        "name": device_name,
                        "type": device_type,
                        "vendor": vendor,
                        "hostname": hostname,
                    }
                )
            except Exception as err:
                _LOGGER.debug("Error parsing host %s: %s", host, err)
                continue

        try:
            devices.sort(key=lambda x: [int(num) for num in x["ip"].split(".")])
        except Exception:
            pass

        return devices
