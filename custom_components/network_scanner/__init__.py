from .sensor import NetworkScanner
from .const import DOMAIN

async def async_setup(hass, config):
    """Set up the Network Scanner component."""
    # Store YAML configuration in hass.data
    hass.data[DOMAIN] = config.get(DOMAIN, {})
    return True

async def async_setup_entry(hass, config_entry):
    """Set up Network Scanner from a config entry."""
    # Pull in any ip_range / mac_mapping_* keys defined in
    # configuration.yaml that aren't already on this config entry. This is
    # what actually makes "Option 2: Manually via configuration.yaml" from
    # the README work post-setup -- previously YAML values were only ever
    # used as suggested defaults in the one-time setup wizard and were
    # silently ignored afterwards, so edits to configuration.yaml appeared
    # to do nothing (requires an HA restart to be picked up, same as any
    # other YAML change).
    yaml_config = hass.data.get(DOMAIN, {})
    if isinstance(yaml_config, dict):
        missing = {
            key: value
            for key, value in yaml_config.items()
            if (key == "ip_range" or key.startswith("mac_mapping_"))
            and key not in config_entry.data
        }
        if missing:
            hass.config_entries.async_update_entry(
                config_entry, data={**config_entry.data, **missing}
            )

    await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor"])

    # Reload the entry whenever it's updated (e.g. via the options flow),
    # so newly added/edited mac_mapping entries take effect immediately
    # instead of requiring the integration to be removed and re-added.
    config_entry.async_on_unload(
        config_entry.add_update_listener(_async_update_listener)
    )

    return True

async def _async_update_listener(hass, config_entry):
    """Handle an update to the config entry by reloading it."""
    await hass.config_entries.async_reload(config_entry.entry_id)

async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    return True
