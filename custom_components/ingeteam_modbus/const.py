DOMAIN = "ingeteam_modbus"
DEFAULT_NAME = "ingeteam"
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_PORT = 502
DEFAULT_MODBUS_ADDRESS = 1
DEFAULT_READ_METER = True
DEFAULT_READ_BATTERY = True

# --- Claves de configuración ---
CONF_MODBUS_ADDRESS = "modbus_address"
CONF_READ_METER = "read_meter"
CONF_READ_BATTERY = "read_battery"

# --- Atributos del dispositivo ---
ATTR_MANUFACTURER = "Ingeteam"

# --- Mapeo de valores de registros a texto legible ---

BOOLEAN_STATUS = {0: "Off", 1: "On"}

INVERTER_STATUS = {
    0: "Stopped",
    1: "Starting",
    2: "Off-grid",
    3: "On-grid",
    4: "On-grid (Standby Battery)",
    5: "Waiting to connect to Grid",
    6: "Critical Loads Bypassed",
    7: "Emergency Charge from PV",
    8: "Emergency Charge from Grid",
    9: "Locked - waiting for Reset",
    10: "Error",
}

BATTERY_STATUS = {
    0: "Standby",
    1: "Discharging",
    2: "Constant Current Charging",
    3: "Constant Voltage Charging",
    4: "Floating",
    5: "Equalizing",
    6: "BMS Communication Error",
    7: "Not Configured",
    8: "Capacity Calibration (Step 1)",
    9: "Capacity Calibration (Step 2)",
    10: "Standby Manual",
}

# NOTE 4 del PDF (Bitmask). Ahora las claves son los valores de los bits (potencias de 2).
BATTERY_BMS_ALARMS = {
    1: "High Current Charge",   # Bit 0
    2: "High Voltage",          # Bit 1
    4: "Low Voltage",           # Bit 2
    8: "High Temperature",      # Bit 3
    16: "Low Temperature",       # Bit 4
    32: "BMS Internal",        # Bit 5
    64: "Cell Imbalance",      # Bit 6
    128: "High Current Discharge",# Bit 7
    256: "System BMS Error",    # Bit 8
}

# NOTE 10 del PDF (Bitmask para BMS Flags).
BATTERY_BMS_FLAGS = {
    1: "Stop Charge",           # Bit 0
    2: "Stop Discharge",        # Bit 1
    4: "Forced Charge (BMS)",   # Bit 2
    8: "Calibration Needed",    # Bit 3
    16: "Forced Charge (SOC)",   # Bit 4
}

# NOTE 9 del PDF
BATTERY_LIMITATION_REASONS = {
    0: "No limitation",
    1: "Heat Sink Temperature",
    2: "PT100 Temperature",
    3: "Low Bus Voltage Protection",
    4: "Battery Settings",
    5: "BMS Communication",
    6: "SOC Max Configured",
    7: "SOC Min Configured",
    8: "Maximum Battery Power",
    9: "Modbus command",
    10: "Digital Input 2",
    11: "Digital Input 3",
    12: "PV Charging scheduling",
    13: "EMS Strategy",
}

# NOTE 7 del PDF
AP_REDUCTION_REASONS = {
    0: "No limitation",
    1: "Communication",
    2: "PCB Temperature",
    3: "Heat Sink Temperature",
    4: "Pac vs Fac Algorithm",
    5: "Soft Start",
    6: "Charge Power Configured",
    7: "PV Surplus injected to the Loads",
    8: "Pac vs Vac Algorithm",
    9: "Battery Power Limited",
    10: "AC Grid Power Limited",
    11: "Self-Consumption Mode",
    12: "High Bus Voltage Protection",
    13: "LVRT or HVRT Process",
    14: "Nominal AC Current",
    15: "Grid Consumption Protection",
    16: "PV Surplus Injected to the Grid",
}
