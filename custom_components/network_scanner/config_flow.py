import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

# Always offer at least this many mac_mapping slots on the form.
MIN_MAC_MAPPING_SLOTS = 25

# Always offer this many *blank* slots past the highest slot already in
# use, so there's always room to add new devices instead of the form
# being sized exactly to what you already have.
EXTRA_BLANK_SLOTS = 15


def _build_schema(current_data):
    """Build the ip_range / mac_mapping schema, pre-filled from current_data.

    Shared by both the initial config flow and the options flow so that
    values entered during setup show back up (and can be edited) later.
    """
    schema_dict = {
        vol.Required(
            "ip_range",
            description={"suggested_value": current_data.get("ip_range", "192.168.1.0/24")},
        ): str
    }

    # Work out how many mac_mapping_N slots we need to show: enough to
    # cover any already-saved entries (e.g. mac_mapping_70), plus a
    # buffer of blank slots so there's always room to add more, plus a
    # floor of MIN_MAC_MAPPING_SLOTS for brand-new entries.
    highest_existing = 0
    for key in current_data:
        if key.startswith("mac_mapping_"):
            suffix = key[len("mac_mapping_"):]
            if suffix.isdigit():
                highest_existing = max(highest_existing, int(suffix))

    max_index = max(MIN_MAC_MAPPING_SLOTS, highest_existing + EXTRA_BLANK_SLOTS)

    for i in range(1, max_index + 1):
        key = f"mac_mapping_{i}"
        schema_dict[
            vol.Optional(key, description={"suggested_value": current_data.get(key)})
        ] = str

    return vol.Schema(schema_dict)


class NetworkScannerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Network Scanner."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Manage the initial setup from the user interface."""
        errors = {}

        # Load data from configuration.yaml
        yaml_config = self.hass.data.get(DOMAIN, {})
        _LOGGER.debug("YAML Config: %s", yaml_config)

        if user_input is not None:
            return self.async_create_entry(title="Network Scanner", data=user_input)

        schema = _build_schema(yaml_config)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={"description": "Enter the IP range and MAC mappings"},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return NetworkScannerOptionsFlow()


class NetworkScannerOptionsFlow(config_entries.OptionsFlow):
    """Handle reconfiguration of an existing Network Scanner entry.

    This is what makes the "Configure" button on the integration work,
    so ip_range and mac_mapping_* entries can be added/edited/removed
    after the integration has already been set up, without having to
    delete and re-add it.
    """

    async def async_step_init(self, user_input=None):
        errors = {}

        if user_input is not None:
            # Drop empty optional fields so they don't linger as blank
            # mac_mapping_N entries once a user clears them out.
            cleaned = {
                k: v
                for k, v in user_input.items()
                if k == "ip_range" or (v is not None and str(v).strip() != "")
            }

            # Persist onto the config entry's data (this is what sensor.py
            # reads from). Updating the entry fires update listeners, which
            # __init__.py uses to reload the sensor with the new values.
            self.hass.config_entries.async_update_entry(self.config_entry, data=cleaned)
            return self.async_create_entry(title="", data={})

        current_data = dict(self.config_entry.data)
        schema = _build_schema(current_data)

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={"description": "Update the IP range and MAC mappings"},
        )
