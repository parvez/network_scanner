# Home Assistant Network Scanner Integration

This Home Assistant integration provides a network scanner that identifies all devices on your local network. Utilizing the provided IP range and MAC address mappings, it gives each identified device a user-friendly name and manufacturer information.

## Features

- Scans the local network based on a user-defined IP range.
- Uses user-provided MAC address to device mapping for easy identification.
- Automatically updates the list of devices on a periodic basis.
- Displays the total number of devices currently identified on the network.

## Installation through HACS

Once this integration is merged into HACS then you can install the network_scanner integration by searching for it there in HA instance.

Until then you will have to add this repository manually:

Go to HACS -> 3 dot menu -> Custom Repositories:-

Paste https://github.com/parvez/network_scanner into Repository field and select Integration

Now you should be able to find it in HACS as normal.

## Manual Installation

To install this integration, copy the `network_scanner` directory into the `custom_components` directory of your Home Assistant installation.

## Configuration

Configure the integration through the Home Assistant UI:

1. Navigate to Configuration > Integrations.
2. Click on the `+ Add Integration` button.
3. Search for "Network Scanner" and select it.
4. Enter the desired IP range for the network scan, e.g., `192.168.1.1-254` or use the CIDR notation like `192.168.1.0/24`.
5. Optionally, provide MAC address to device mapping in the format in `configuration.yaml`:
   - MAC address (e.g., `bc:14:14:f1:81:1b`)
   - Friendly name (e.g., `Brother Printer`)
   - Manufacturer (e.g., `Cloud Network Technology Singapore Pte. Ltd.`)
6. Separate each field with a semi-colon and each mapping entry with a newline.

Example of entries in the config flow input fields:

```plaintext
bc:14:14:f1:81:1b;Brother Printer;Cloud Network Technology Singapore Pte. Ltd.
b1:81:11:31:a1:b1;My iPhone;Apple Inc.
```

<img width="350" alt="Configuration Flow Example" src="https://github.com/parvez/network_scanner/assets/126749/bf08bc6d-a4a1-478c-8acb-5beffada2632">

*Refer to the configuration flow image provided for a visual guide.*


## Displaying Devices in the UI using Markdown Card

To visualize the devices detected by the Network Scanner in the Home Assistant interface, you can add a Lovelace Markdown card with the following configuration:

```yaml
type: markdown
content: >
  ## Devices

  | IP Address | MAC Address | Custom Name | Custom Description | Hostname | Vendor |
  |------------|-------------|-------------|--------------------|----------|--------|

  {% for device in state_attr('sensor.network_scanner', 'devices') %}
  | {{ device.ip }} | {{ device.mac }} | {{ device.name }} | {{ device.type }} | {{ device.hostname }} | {{ device.vendor }} |
  {% endfor %}
```

This card will display a table with the IP Address, MAC Address, and Vendor of each device that has been scanned in your network. Name and Type are custom mapping provided by the user. Here's how it will look:

<img width="800" alt="Network Scanner Device List" src="https://github.com/parvez/network_scanner/assets/126749/64309b93-a8cd-43b6-93ab-58d55a4aac32">

## Displaying Devices in the UI using Flex Table

Thanks to [@gridlockjoe](https://github.com/gridlockjoe), you can also display using the [Flex Table](https://github.com/custom-cards/flex-table-card) as such

```yaml
type: custom:flex-table-card
title: Devices
entities:
  include: sensor.network_scanner
sort_by: x.ip+
columns:
  - name: IP Address
    data: devices
    modify: x.ip
  - name: MAC Address
    data: devices
    modify: x.mac
  - name: Custom Name
    data: devices
    modify: x.name
  - name: Custom Description
    data: devices
    modify: x.type
  - name: Hostname
    data: devices
    modify: x.hostname
  - name: Vendor
    data: devices
    modify: x.vendor
```
<img width="800" alt="Network Scanner Device List" src="https://github.com/parvez/network_scanner/assets/126749/b55f58ee-2f89-415f-b09b-fc457e52a074">


## Technical Details

The integration is composed of several Python scripts that manage the setup and updating of the network sensor:

- `config_flow.py`: Handles the user interface for configuration.
- `const.py`: Contains constants used by the integration.
- `__init__.py`: Sets up and unloads the integration components.
- `sensor.py`: Defines the Network Scanner sensor, including methods for scanning the network and parsing the MAC address mapping.

The network scan is performed every 15 minutes by default, and the results are logged for debugging purposes. The `nmap` library is used to scan the network, and the `async_setup_entry` function in `sensor.py` initializes the sensor with the IP range and MAC mappings specified in the configuration.

## Troubleshooting

If you encounter any issues:

- Check the Home Assistant logs for errors related to the network scanner.
- Ensure that the IP range and MAC address mappings are correctly formatted.
- Verify that `nmap` is installed and accessible to the Home Assistant environment.

## Contributing

Contributions to this integration are welcome. Please refer to the project's GitHub repository for contributing guidelines.

