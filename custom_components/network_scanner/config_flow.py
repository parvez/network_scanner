import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN

class NetworkScannerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Network Scanner."""

    async def async_step_user(self, user_input=None):
        """Manage the configurations from the user interface."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="Network Scanner", data=user_input)

        data_schema = vol.Schema({
            vol.Required("ip_range", description={"suggested_value": "192.168.1.0/24"}): str,
            **{vol.Optional(f"mac_mapping_{i+1}"): str for i in range(25)},
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"description": "Enter the IP range and MAC mappings"}
        )
