import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

class NetworkScannerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Network Scanner."""

    async def async_step_user(self, user_input=None):
        def format_dict_for_printing(d):
            return {k: str(v) for k, v in d.items()}

        """Manage the configurations from the user interface."""
        errors = {}

        # Load data from configuration.yaml
        yaml_config = self.hass.data.get(DOMAIN, {})
        _LOGGER.debug("YAML Config: %s", yaml_config)

        if user_input is not None:
            return self.async_create_entry(title="Network Scanner", data=user_input)

        data_schema_dict = {
            vol.Required("ip_range", description={"suggested_value": yaml_config.get("ip_range", "192.168.1.0/24")}): str
        }

        # Add mac mappings with values from YAML if available
        for i in range(1, 26):  # Ensure at least 25 entries
            key = f"mac_mapping_{i}"
            if key in yaml_config:
                suggested_value = yaml_config.get(key)
                _LOGGER.debug("YAML Config key: %s", suggested_value)
            else:
                suggested_value = None  # No value in YAML config
            
            # Add the optional field to the schema, with or without suggested_value
            data_schema_dict[vol.Optional(key, description={"suggested_value": suggested_value})] = str

        # Continue to add more mappings if available in the YAML config
        i = 26
        while True:
            key = f"mac_mapping_{i}"
            if key in yaml_config:
                suggested_value = yaml_config.get(key)
                _LOGGER.debug("YAML Config key: %s", suggested_value)
                data_schema_dict[vol.Optional(key, description={"suggested_value": suggested_value})] = str
                i += 1
            else:
                break  # Exit loop when no more mappings are found in the YAML config

        _LOGGER.debug("schema: %s", format_dict_for_printing(data_schema_dict))
        data_schema = vol.Schema(data_schema_dict)

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"description": "Enter the IP range and MAC mappings"}
        )
