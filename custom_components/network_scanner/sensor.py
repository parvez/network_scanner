import logging
import subprocess
import json
from datetime import timedelta
from homeassistant.helpers.entity import Entity

SCAN_INTERVAL = timedelta(minutes=15)

_LOGGER = logging.getLogger(__name__)

class NetworkScanner(Entity):
    """Representation of a Network Scanner."""

    def __init__(self, hass, ip_range, mac_mapping):
        """Initialize the sensor."""
        self._state = None
        self.hass = hass
        self.ip_range = ip_range
        self.mac_mapping = self.parse_mac_mapping(mac_mapping)
        _LOGGER.info("Network Scanner initialized")

    @property
    def name(self):
        return 'Network Scanner'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'Devices'

    async def async_update(self):
        """Fetch new state data for the sensor."""
        try:
            _LOGGER.debug("Scanning network")
            devices = await self.hass.async_add_executor_job(self.scan_network)
            self._state = len(devices)
            self._attr_extra_state_attributes = {"devices": devices}
        except Exception as e:
            _LOGGER.error("Error updating network scanner: %s", e)

    def parse_mac_mapping(self, mapping_string):
        """Parse the MAC mapping string into a dictionary."""
        mapping = {}
        for line in mapping_string.split('\n'):
            parts = line.split('\t')
            if len(parts) >= 3:
                mapping[parts[0].lower()] = (parts[1], parts[2])
        return mapping

    def get_device_info_from_mac(self, mac_address):
        """Retrieve device name and type from the MAC mapping."""
        return self.mac_mapping.get(mac_address.lower(), ("Unknown Device", "Unknown Device"))

    def scan_network(self):
        """Scan the network and return device information."""
        devices = []
        nmap_command = f'nmap -sn {self.ip_range} -oG -'
        nmap_output = subprocess.check_output(nmap_command, shell=True, text=True)

        for line in nmap_output.splitlines():
            if "Up" in line:
                ip = line.split()[1]
                arp_command = f'arp -n | awk -v ip="{ip}" \'$1 == ip && $3 != "00:00:00:00:00:00" {{print $3}}\''
                mac = subprocess.check_output(arp_command, shell=True, text=True).strip()
                if mac:
                    device_name, device_type = self.get_device_info_from_mac(mac)
                    devices.append({
                        "ip": ip,
                        "mac": mac,
                        "name": device_name,
                        "type": device_type
                    })

        return devices
