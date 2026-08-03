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
            _LOGGER.debug("Found Host: %s", host)
            if 'mac' in self.nm[host]['addresses']:
                _LOGGER.debug("Found Mac: %s", self.nm[host]['addresses'])
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

    # Collect every mac_mapping_N key present in the entry, regardless of
    # numbering gaps. Previously this walked mac_mapping_26, 27, 28...
    # contiguously and stopped at the first missing key, which meant
    # deleting/clearing a single entry in the middle (e.g. mac_mapping_40)
    # would silently drop every entry numbered above it, even though their
    # data was still stored. Sorting and including whatever keys actually
    # exist avoids that entirely.
    def _slot_number(key):
        suffix = key[len("mac_mapping_"):]
        return int(suffix) if suffix.isdigit() else 0

    mapping_items = sorted(
        (
            (key, value)
            for key, value in config_entry.data.items()
            if key.startswith("mac_mapping_") and value
        ),
        key=lambda item: _slot_number(item[0]),
    )
    for key, value in mapping_items:
        _LOGGER.debug("%s: %s", key, value)

    # Combine mac mappings into a newline-separated string
    mac_mappings = "\n".join(value for _, value in mapping_items)
    _LOGGER.debug("mac_mappings: %s", mac_mappings)

    # Set up the network scanner entity
    scanner = NetworkScanner(hass, ip_range, mac_mappings)
    async_add_entities([scanner], True)
