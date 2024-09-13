import logging
import nmap
from datetime import timedelta
from homeassistant.helpers.entity import Entity
from .const import DOMAIN

SCAN_INTERVAL = timedelta(minutes=15)

_LOGGER = logging.getLogger(__name__)

class NetworkScanner(Entity):
    """Representation of a Network Scanner."""

    def __init__(self, hass, ip_range, mac_mapping):
        """Initialize the sensor."""
        self._state = None
        self.hass = hass
        self.ip_range = ip_range

        _LOGGER.debug("mac_mapping unparsed: %s", mac_mapping)
        self.mac_mapping = self.parse_mac_mapping(mac_mapping)
        _LOGGER.debug("mac_mapping parsed: %s", mac_mapping)

        self.nm = nmap.PortScanner()
        _LOGGER.info("Network Scanner initialized")

    @property
    def should_poll(self):
        """Return True as updates are needed via polling."""
        return True

    @property
    def unique_id(self):
        """Return unique ID."""
        return f"network_scanner_{self.ip_range}"

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
            parts = line.split(';')
            if len(parts) >= 3:
                mapping[parts[0].lower()] = (parts[1], parts[2])
        return mapping

    def get_device_info_from_mac(self, mac_address):
        """Retrieve device name and type from the MAC mapping."""
        return self.mac_mapping.get(mac_address.lower(), ("Unknown Device", "Unknown Device"))

    def scan_network(self):
        """Scan the network and return device information."""
        self.nm.scan(hosts=self.ip_range, arguments='-sn')
        devices = []

        for host in self.nm.all_hosts():
            if 'mac' in self.nm[host]['addresses']:
                ip = self.nm[host]['addresses']['ipv4']
                mac = self.nm[host]['addresses']['mac']
                vendor = "Unknown"
                if 'vendor' in self.nm[host] and mac in self.nm[host]['vendor']:
                    vendor = self.nm[host]['vendor'][mac]
                hostname = self.nm[host].hostname()
                device_name, device_type = self.get_device_info_from_mac(mac)
                devices.append({
                    "ip": ip,
                    "mac": mac,
                    "name": device_name,
                    "type": device_type,
                    "vendor": vendor,
                    "hostname": hostname
                })

        # Sort the devices by IP address
        devices.sort(key=lambda x: [int(num) for num in x['ip'].split('.')])
        return devices

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Network Scanner sensor from a config entry."""
    ip_range = config_entry.data.get("ip_range")
    _LOGGER.debug("ip_range: %s", config_entry.data.get("ip_range"))
    
    # Initialize mac_mappings list to ensure at least 25 entries
    mac_mappings_list = []

    # Ensure we have at least 25 entries, even if config is missing some
    for i in range(25):
        key = f"mac_mapping_{i+1}"
        mac_mapping = config_entry.data.get(key, "")
        mac_mappings_list.append(mac_mapping)
        _LOGGER.debug("mac_mapping_%s: %s", i+1, mac_mapping)

    # Continue adding additional mac mappings if present in the config
    i = 25
    while True:
        key = f"mac_mapping_{i+1}"
        if key in config_entry.data:
            mac_mapping = config_entry.data.get(key)
            mac_mappings_list.append(mac_mapping)
            _LOGGER.debug("mac_mapping_%s: %s", i+1, mac_mapping)
            i += 1
        else:
            break

    # Combine mac mappings into a newline-separated string
    mac_mappings = "\n".join(mac_mappings_list)
    _LOGGER.debug("mac_mappings: %s", mac_mappings)

    # Set up the network scanner entity
    scanner = NetworkScanner(hass, ip_range, mac_mappings)
    async_add_entities([scanner], True)
