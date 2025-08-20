from __future__ import annotations
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo

from .const import ATTR_MANUFACTURER, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Definición centralizada y completa de todos los sensores del PDF
SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    # --- Inverter Status ---
    SensorEntityDescription(key="status", name="Status", icon="mdi:solar-power"),
    SensorEntityDescription(key="stop_code", name="Stop Event Code", icon="mdi:alert-circle-outline", entity_registry_enabled_default=False),
    SensorEntityDescription(key="alarm_code", name="Alarm Code", icon="mdi:alert-circle-outline", entity_registry_enabled_default=False),
    SensorEntityDescription(key="waiting_time", name="Waiting Time to Connect", native_unit_of_measurement="s", icon="mdi:timer-sand"),
    SensorEntityDescription(key="total_operation_time", name="Total Operation Time", native_unit_of_measurement="h", icon="mdi:clock-outline", entity_registry_enabled_default=True),

    # --- Inverter Power & Loads ---
    SensorEntityDescription(key="active_power", name="Active Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="reactive_power", name="Reactive Power", native_unit_of_measurement="var", device_class=SensorDeviceClass.REACTIVE_POWER, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="power_factor", name="Power Factor Cosφ", device_class=SensorDeviceClass.POWER_FACTOR, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="ap_reduction_ratio", name="Active Power Reduction Ratio", native_unit_of_measurement=PERCENTAGE, icon="mdi:arrow-collapse-down"),
    SensorEntityDescription(key="ap_reduction_reason", name="Active Power Reduction Reason", icon="mdi:information-outline"),
    SensorEntityDescription(key="reactive_setpoint_type", name="Reactive Power Set-Point Type", icon="mdi:information-outline"),

    # --- Critical Loads ---
    SensorEntityDescription(key="total_loads_power", name="Total Loads Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, icon="mdi:power-plug"),
    SensorEntityDescription(key="cl_active_power", name="Critical Loads Active Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="cl_voltage", name="Critical Loads Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="cl_current", name="Critical Loads Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="cl_freq", name="Critical Loads Frequency", native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="cl_reactive_power", name="Critical Loads Reactive Power", native_unit_of_measurement="var", device_class=SensorDeviceClass.REACTIVE_POWER, state_class=SensorStateClass.MEASUREMENT),
    
    # --- PV Data ---
    SensorEntityDescription(key="pv1_power", name="PV1 Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, icon="mdi:solar-power"),
    SensorEntityDescription(key="pv1_voltage", name="PV1 Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="pv1_current", name="PV1 Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="pv2_power", name="PV2 Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, icon="mdi:solar-power"),
    SensorEntityDescription(key="pv2_voltage", name="PV2 Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="pv2_current", name="PV2 Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="pv_internal_total_power", name="PV Internal Total Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, icon="mdi:solar-power"),
    SensorEntityDescription(key="pv_total_power", name="PV Total Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, icon="mdi:solar-power"),
    SensorEntityDescription(key="external_pv_power", name="PV External Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, entity_registry_enabled_default=False),
    SensorEntityDescription(key="ev_power", name="EV Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, icon="mdi:ev-station"),

    # --- Inverter Diagnostics ---
    SensorEntityDescription(key="dc_bus_voltage", name="DC Bus Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="rms_diff_current", name="RMS Differential Current", native_unit_of_measurement="mA", icon="mdi:current-ac"),
    SensorEntityDescription(key="temp_pcb", name="Internal Temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="temp_mod_1", name="Temperature Module 1", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="temp_mod_2", name="Temperature Module 2", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="positive_isolation_resistance", name="Positive Isolation Resistance", native_unit_of_measurement="kOhm", icon="mdi:check-network-outline", entity_registry_enabled_default=False),
    SensorEntityDescription(key="negative_isolation_resistance", name="Negative Isolation Resistance", native_unit_of_measurement="kOhm", icon="mdi:close-network-outline", entity_registry_enabled_default=False),

    # --- Digital I/O Status ---
    SensorEntityDescription(key="di_2_status", name="Digital Input 2 Status", icon="mdi:electric-switch"),
    SensorEntityDescription(key="di_3_status", name="Digital Input 3 Status", icon="mdi:electric-switch"),
    SensorEntityDescription(key="di_drm_status", name="Digital Input DRM0 Status", icon="mdi:electric-switch"),
    SensorEntityDescription(key="do_1_status", name="Digital Output 1 Status", icon="mdi:electric-switch"),
    SensorEntityDescription(key="do_2_status", name="Digital Output 2 Status", icon="mdi:electric-switch"),
)

BATTERY_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(key="battery_status", name="Battery Status", icon="mdi:battery"),
    SensorEntityDescription(key="battery_state_of_charge", name="Battery State of Charge", native_unit_of_measurement=PERCENTAGE, device_class=SensorDeviceClass.BATTERY, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="battery_charging_power", name="Battery Charging Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="battery_discharging_power", name="Battery Discharging Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="battery_voltage", name="Battery Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="battery_current", name="Battery Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="battery_temp", name="Battery Temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="battery_state_of_health", name="Battery State of Health", native_unit_of_measurement=PERCENTAGE, icon="mdi:battery-heart-variant"),
    SensorEntityDescription(key="battery_charging_voltage", name="Battery Charging Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE),
    SensorEntityDescription(key="battery_discharging_voltage", name="Battery Discharging Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE),
    SensorEntityDescription(key="battery_charging_current_max", name="Battery Max. Charging Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT),
    SensorEntityDescription(key="battery_discharging_current_max", name="Battery Max. Discharging Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT),
    SensorEntityDescription(key="battery_bms_alarm", name="Battery BMS Alarm", icon="mdi:battery-alert"),
    SensorEntityDescription(key="battery_discharge_limitation_reason", name="Battery Discharge Limitation Reason", icon="mdi:information-outline"),
    SensorEntityDescription(key="battery_voltage_internal", name="Battery Voltage Internal Sensor", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE),
    SensorEntityDescription(key="battery_bms_warnings", name="Battery BMS Warnings", icon="mdi:battery-alert"),
    SensorEntityDescription(key="battery_bms_errors", name="Battery BMS Errors", icon="mdi:battery-alert"),
    SensorEntityDescription(key="battery_bms_faults", name="Battery BMS Faults", icon="mdi:battery-alert"),
    SensorEntityDescription(key="battery_bms_flags", name="Battery BMS Flags", icon="mdi:flag"),
)

METER_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    # External Meter
    SensorEntityDescription(key="em_active_power", name="Grid Consumption Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="em_active_power_returned", name="Grid Export Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="em_voltage", name="Grid Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="em_freq", name="Grid Frequency", native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="em_reactive_power", name="Grid Reactive Power", native_unit_of_measurement="var", device_class=SensorDeviceClass.REACTIVE_POWER, state_class=SensorStateClass.MEASUREMENT, entity_registry_enabled_default=False),
    # Internal Meter
    SensorEntityDescription(key="im_voltage", name="Internal Meter Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="im_current", name="Internal Meter Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="im_freq", name="Internal Meter Frequency", native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="im_active_power", name="Internal Meter Active Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="im_reactive_power", name="Internal Meter Reactive Power", native_unit_of_measurement="var", device_class=SensorDeviceClass.REACTIVE_POWER, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="im_power_factor", name="Internal Power Factor Cosφ", device_class=SensorDeviceClass.POWER_FACTOR, state_class=SensorStateClass.MEASUREMENT),
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Ingeteam modbus sensors from a config entry."""
    hub = hass.data[DOMAIN][entry.data["name"]]["hub"]

    device_info = DeviceInfo(
        identifiers={(DOMAIN, hub.name)},
        name=hub.name,
        manufacturer=ATTR_MANUFACTURER,
    )

    descriptions_to_create = list(SENSOR_DESCRIPTIONS)
    if hub.read_battery:
        descriptions_to_create.extend(BATTERY_DESCRIPTIONS)
    if hub.read_meter:
        descriptions_to_create.extend(METER_DESCRIPTIONS)

    entities = [
        IngeteamSensor(hub, device_info, description)
        for description in descriptions_to_create
    ]
    async_add_entities(entities)


class IngeteamSensor(SensorEntity):
    """Representation of an Ingeteam Modbus sensor using the hub's custom callback."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub, device_info: DeviceInfo, description: SensorEntityDescription):
        """Initialize the sensor."""
        self._hub = hub
        self.entity_description = description
        self._attr_device_info = device_info
        self._attr_unique_id = f"{hub.name}_{description.key}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        value = self._hub.data.get(self.entity_description.key)
        if self.device_class == SensorDeviceClass.POWER_FACTOR and isinstance(value, float):
            return round(value, 3)
        return value

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self._hub.async_add_ingeteam_sensor(self._modbus_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callbacks."""
        self._hub.async_remove_ingeteam_sensor(self._modbus_data_updated)

    @callback
    def _modbus_data_updated(self) -> None:
        """Update HA state when hub data changes."""
        self.async_write_ha_state()
