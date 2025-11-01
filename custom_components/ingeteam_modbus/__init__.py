"""The Ingeteam Modbus Integration."""
import asyncio
import logging
import threading
from datetime import timedelta
from typing import Optional

import voluptuous as vol
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MODBUS_ADDRESS,
    CONF_MODBUS_ADDRESS,
    CONF_READ_METER,
    CONF_READ_BATTERY,
    DEFAULT_READ_METER,
    DEFAULT_READ_BATTERY,
    BOOLEAN_STATUS,
    INVERTER_STATUS,
    BATTERY_STATUS,
    BATTERY_BMS_ALARMS,
    BATTERY_LIMITATION_REASONS,
    AP_REDUCTION_REASONS,
)

_LOGGER = logging.getLogger(__name__)

INGETEAM_MODBUS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.string,
        vol.Optional(CONF_MODBUS_ADDRESS, default=DEFAULT_MODBUS_ADDRESS): cv.positive_int,
        vol.Optional(CONF_READ_METER, default=DEFAULT_READ_METER): cv.boolean,
        vol.Optional(CONF_READ_BATTERY, default=DEFAULT_READ_BATTERY): cv.boolean,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
    }
)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({cv.slug: INGETEAM_MODBUS_SCHEMA})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor"]


async def async_setup(hass, config):
    """Set up the Ingeteam modbus component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up a ingeteam mobus."""
    host = entry.data[CONF_HOST]
    name = entry.data[CONF_NAME]
    port = entry.data[CONF_PORT]
    address = entry.data.get(CONF_MODBUS_ADDRESS, 1)
    scan_interval = entry.data[CONF_SCAN_INTERVAL]
    read_meter = entry.data.get(CONF_READ_METER, False)
    read_battery = entry.data.get(CONF_READ_BATTERY, False)

    _LOGGER.debug("Setup %s.%s", DOMAIN, name)

    hub = IngeteamModbusHub(
        hass,
        name,
        host,
        port,
        address,
        scan_interval,
        read_meter,
        read_battery,
    )

    """Register the hub."""
    hass.data[DOMAIN][name] = {"hub": hub}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    """Unload Ingeteam mobus entry."""
    hub: "IngeteamModbusHub" = hass.data[DOMAIN][entry.data["name"]]["hub"]
    hub.close()

    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, component) for component in PLATFORMS]
        )
    )
    if not unload_ok:
        return False

    hass.data[DOMAIN].pop(entry.data["name"])
    return True


class IngeteamModbusHub:
    """Thread safe wrapper class for pymodbus."""

    def __init__(self, hass, name, host, port, address, scan_interval, read_meter=True, read_battery=False):
        """Initialize the Modbus hub."""
        self._hass = hass
        # Nota: no fijamos versiones. Construimos el cliente estándar.
        # En pymodbus 3.x las firmas han cambiado, por eso la lectura es robusta abajo.
        self._client = ModbusTcpClient(host=host, port=port, timeout=max(3, (scan_interval - 1)))
        self._lock = threading.Lock()
        self._name = name
        self._address = address
        self._host = host
        self._port = port
        self.read_meter = read_meter
        self.read_battery = read_battery
        self._scan_interval = timedelta(seconds=scan_interval)
        self._unsub_interval_method = None
        self._sensors = []
        self.data = {}

    @callback
    def async_add_ingeteam_sensor(self, update_callback):
        """Listen for data updates."""
        if not self._sensors:
            self.connect()
            self._unsub_interval_method = async_track_time_interval(
                self._hass, self.async_refresh_modbus_data, self._scan_interval
            )
        self._sensors.append(update_callback)

    @callback
    def async_remove_ingeteam_sensor(self, update_callback):
        """Remove data update."""
        self._sensors.remove(update_callback)
        if not self._sensors and self._unsub_interval_method:
            self._unsub_interval_method()
            self._unsub_interval_method = None
            self.close()

    async def async_refresh_modbus_data(self, _now: Optional[int] = None) -> None:
        """Time to update."""
        if not self._sensors:
            return
        update_result = await self._hass.async_add_executor_job(self._update_modbus_data)
        if update_result:
            for update_callback in self._sensors:
                update_callback()

    def _update_modbus_data(self) -> bool:
        """Synchronously fetch data from the modbus device. To be run in an executor."""
        if not self._check_and_reconnect():
            return False
        try:
            return self.read_modbus_data()
        except ModbusException as e:
            _LOGGER.warning("Modbus exception occurred while reading data: %s", e)
            return False
        except Exception:
            _LOGGER.exception("Unexpected error while reading modbus data")
            return False

    @property
    def name(self):
        """Return the name of this hub."""
        return self._name

    def close(self):
        """Disconnect client."""
        with self._lock:
            try:
                self._client.close()
            except Exception:
                _LOGGER.debug("Error closing Modbus client", exc_info=True)

    def _check_and_reconnect(self) -> bool:
        """Check connection and reconnect if needed."""
        with self._lock:
            try:
                # Algunos clientes exponen is_socket_open, otros no
                is_open = getattr(self._client, "is_socket_open", None)
                if callable(is_open):
                    open_ok = is_open()
                else:
                    # fallback: intentamos una conexión liviana si no hay método
                    open_ok = False
                if not open_ok:
                    _LOGGER.info("Modbus client is not connected, trying to reconnect")
                    return self._client.connect()
                return True
            except Exception:
                _LOGGER.debug("Error comprobando conexión Modbus, intentando reconectar", exc_info=True)
                return self._client.connect()

    def connect(self) -> bool:
        """Connect client."""
        with self._lock:
            try:
                result = self._client.connect()
                if result:
                    _LOGGER.info("Successfully connected to %s:%s", self._host, self._port)
                else:
                    _LOGGER.warning("Could not connect to %s:%s", self._host, self._port)
                return result
            except Exception:
                _LOGGER.exception("Exception connecting to %s:%s", self._host, self._port)
                return False

    def read_input_registers(self, unit, address, count):
        """Read input registers.

        Esta función intenta múltiples variantes para ser compatible con distintas versiones
        de pymodbus (device_id / unit / slave / unit_id / slaveaddress) y, si es necesario,
        construye un request explícito usando ReadInputRegistersRequest desde posibles rutas.
        """
        with self._lock:
            # 1) Intentar variantes directas (compatibilidad máxima)
            try:
                return self._client.read_input_registers(address=address, count=count, device_id=unit)
            except TypeError:
                pass
            except Exception as e:
                _LOGGER.debug("read_input_registers(device_id=..) fallo: %s", e, exc_info=True)

            try:
                return self._client.read_input_registers(address=address, count=count, unit=unit)
            except TypeError:
                pass
            except Exception as e:
                _LOGGER.debug("read_input_registers(unit=..) fallo: %s", e, exc_info=True)

            try:
                return self._client.read_input_registers(address=address, count=count, slave=unit)
            except TypeError:
                pass
            except Exception as e:
                _LOGGER.debug("read_input_registers(slave=..) fallo: %s", e, exc_info=True)

            try:
                return self._client.read_input_registers(address=address, count=count, unit_id=unit)
            except TypeError:
                pass
            except Exception as e:
                _LOGGER.debug("read_input_registers(unit_id=..) fallo: %s", e, exc_info=True)

            try:
                return self._client.read_input_registers(address=address, count=count, slaveaddress=unit)
            except TypeError:
                pass
            except Exception as e:
                _LOGGER.debug("read_input_registers(slaveaddress=..) fallo: %s", e, exc_info=True)

            # 2) Intentar uso de Request object (varias rutas de import posibles)
            ReadInputReq = None
            import_errors = []
            try:
                # ruta posible: pymodbus.register_read_message.ReadInputRegistersRequest
                from pymodbus.register_read_message import ReadInputRegistersRequest as _RIR
                ReadInputReq = _RIR
            except Exception as e:
                import_errors.append(("pymodbus.register_read_message", e))
                try:
                    # ruta posible: pymodbus.pdu.register_message.ReadInputRegistersRequest
                    from pymodbus.pdu.register_message import ReadInputRegistersRequest as _RIR2
                    ReadInputReq = _RIR2
                except Exception as e2:
                    import_errors.append(("pymodbus.pdu.register_message", e2))
                    try:
                        # ruta alternativa: pymodbus.pdu.ReadInputRegistersRequest (poco común)
                        from pymodbus.pdu import ReadInputRegistersRequest as _RIR3
                        ReadInputReq = _RIR3
                    except Exception as e3:
                        import_errors.append(("pymodbus.pdu", e3))
                        ReadInputReq = None

            if ReadInputReq is not None:
                try:
                    # Construimos request pasando 'slave' (id del equipo) si la clase lo acepta.
                    req = ReadInputReq(address=address, count=count, slave=unit)
                    # ejecutar la petición
                    return self._client.execute(req)
                except TypeError:
                    # Si la clase no acepta 'slave' probamos sin él
                    try:
                        req = ReadInputReq(address=address, count=count)
                        return self._client.execute(req)
                    except Exception as e:
                        _LOGGER.debug("Execute ReadInputRegistersRequest sin slave falló: %s", e, exc_info=True)
                except Exception as e:
                    _LOGGER.debug("Error ejecutando ReadInputRegistersRequest: %s", e, exc_info=True)

            # 3) Si todo falla, mostrar import_errors para depuración y devolver None
            _LOGGER.error(
                "No se pudo invocar read_input_registers con ninguna firma conocida. "
                "Errores de importación: %s",
                "; ".join(f"{p}:{err}" for p, err in import_errors),
            )
            return None

    # -------------------------
    # Utilidades de decodificación
    # -------------------------
    @staticmethod
    def _decode_signed(value: int) -> int:
        """Decode a 16-bit signed integer (two's complement)."""
        if value & 0x8000:
            return value - 0x10000
        return value

    @staticmethod
    def _u32_from_words_le(registers, start_index: int) -> int:
        """
        Combina dos registros de 16 bits en un uint32.
        Orden de palabras 'little' (wordorder LITTLE): low word primero.
        Cada palabra mantiene su endianness de bytes (como en BIG del decoder original),
        por lo que basta con desplazar 16 bits la palabra alta.
        """
        low = registers[start_index]
        high = registers[start_index + 1]
        return (high << 16) | low

    # -------------------------
    # Lectura y parseo principal
    # -------------------------
    def read_modbus_data(self) -> bool:
        """Read and decode all registers in a single, optimized function."""
        all_regs_response = self.read_input_registers(unit=self._address, address=0, count=81)
        if all_regs_response is None:
            _LOGGER.error("No se obtuvo respuesta de read_input_registers (None).")
            return False

        # Algunos responses devuelven errores con método isError()
        try:
            if hasattr(all_regs_response, "isError") and all_regs_response.isError():
                _LOGGER.error("Error reading modbus registers: %s", all_regs_response)
                return False
        except Exception:
            _LOGGER.debug("No se pudo comprobar isError() en la respuesta", exc_info=True)

        # extraer registros si existen
        if not hasattr(all_regs_response, "registers"):
            _LOGGER.error("Respuesta Modbus sin atributo 'registers': %s", all_regs_response)
            return False

        registers = all_regs_response.registers
        if len(registers) < 81:
            _LOGGER.warning(
                "Incomplete Modbus response, expected 81 registers but got %s", len(registers)
            )
            return False

        # --- Inverter Status & Lifetime ---
        # Antes usabas BinaryPayloadDecoder con byteorder=BIG, wordorder=LITTLE (dos registros: 30007-30008)
        self.data["total_operation_time"] = self._u32_from_words_le(registers, 6)  # Reg 30007-8

        self.data["stop_code"] = registers[9]  # Reg 30010

        # Alarm code (30011-30012) → mismo esquema de 32 bits
        self.data["alarm_code"] = self._u32_from_words_le(registers, 10)  # Reg 30011-12

        status_code = registers[15]  # Reg 30016
        self.data["status"] = INVERTER_STATUS.get(status_code, f"Unknown ({status_code})")
        self.data["waiting_time"] = registers[16]  # Reg 30017

        # --- Battery Data ---
        self.data["battery_voltage"] = registers[17] / 10.0
        self.data["battery_current"] = self._decode_signed(registers[18]) / 100.0
        battery_power = self._decode_signed(registers[19])
        self.data["battery_discharging_power"] = max(0, battery_power)
        self.data["battery_charging_power"] = max(0, -battery_power)
        self.data["battery_state_of_charge"] = registers[20]
        self.data["battery_state_of_health"] = registers[21]
        self.data["battery_charging_voltage"] = registers[22] / 10.0
        self.data["battery_discharging_voltage"] = registers[23] / 10.0
        self.data["battery_charging_current_max"] = registers[24] / 100.0
        self.data["battery_discharging_current_max"] = registers[25] / 100.0
        batt_status_code = registers[26]
        self.data["battery_status"] = BATTERY_STATUS.get(batt_status_code, f"Unknown ({batt_status_code})")
        self.data["battery_temp"] = self._decode_signed(registers[27]) / 10.0
        self.data["battery_bms_alarm"] = registers[28]
        batt_limit_code = registers[29]
        self.data["battery_discharge_limitation_reason"] = BATTERY_LIMITATION_REASONS.get(
            batt_limit_code, f"Unknown ({batt_limit_code})"
        )
        self.data["battery_voltage_internal"] = registers[30] / 10.0
        self.data["battery_bms_flags"] = registers[68]  # Reg 30069
        self.data["battery_bms_warnings"] = registers[73]  # Reg 30074
        self.data["battery_bms_errors"] = registers[74]  # Reg 30075
        self.data["battery_bms_faults"] = registers[75]  # Reg 30076
        self.data["battery_charge_limitation_reason"] = registers[77]  # Reg 30078

        # --- PV Data ---
        self.data["pv1_voltage"] = registers[31]
        self.data["pv1_current"] = registers[32] / 100.0
        self.data["pv1_power"] = registers[33]
        self.data["pv2_voltage"] = registers[34]
        self.data["pv2_current"] = registers[35] / 100.0
        self.data["pv2_power"] = registers[36]
        self.data["external_pv_power"] = registers[79]
        self.data["ev_power"] = self._decode_signed(registers[80])
        self.data["pv_internal_total_power"] = self.data.get("pv1_power", 0) + self.data.get("pv2_power", 0)
        self.data["pv_total_power"] = self.data["pv_internal_total_power"] + self.data.get("external_pv_power", 0)

        # --- Inverter & Loads Data ---
        self.data["active_power"] = self._decode_signed(registers[37])
        self.data["reactive_power"] = self._decode_signed(registers[38])
        self.data["power_factor"] = self._decode_signed(registers[39]) / 1000.0
        self.data["ap_reduction_ratio"] = registers[40] / 10.0
        ap_reason_code = registers[41]
        self.data["ap_reduction_reason"] = AP_REDUCTION_REASONS.get(ap_reason_code, f"Unknown ({ap_reason_code})")
        self.data["reactive_setpoint_type"] = registers[42]
        self.data["cl_voltage"] = registers[43]
        self.data["cl_current"] = registers[44] / 100.0
        self.data["cl_freq"] = registers[45] / 100.0
        self.data["cl_active_power"] = self._decode_signed(registers[46])
        self.data["cl_reactive_power"] = self._decode_signed(registers[47])
        self.data["total_loads_power"] = registers[78]
        self.data["dc_bus_voltage"] = registers[54]
        self.data["positive_isolation_resistance"] = registers[59]  # Reg 30060
        self.data["negative_isolation_resistance"] = registers[60]  # Reg 30061
        self.data["temp_mod_1"] = self._decode_signed(registers[55]) / 10.0
        self.data["temp_mod_2"] = self._decode_signed(registers[56]) / 10.0
        self.data["temp_pcb"] = self._decode_signed(registers[57]) / 10.0
        self.data["rms_diff_current"] = registers[61] / 10.0
        self.data["do_1_status"] = BOOLEAN_STATUS.get(registers[62], "Unknown")
        self.data["do_2_status"] = BOOLEAN_STATUS.get(registers[63], "Unknown")
        self.data["di_drm_status"] = BOOLEAN_STATUS.get(registers[64], "Unknown")
        self.data["di_2_status"] = BOOLEAN_STATUS.get(registers[65], "Unknown")
        self.data["di_3_status"] = BOOLEAN_STATUS.get(registers[66], "Unknown")

        # --- Meter Data ---
        self.data["im_voltage"] = registers[48]
        self.data["im_current"] = registers[49] / 100.0
        self.data["im_freq"] = registers[50] / 100.0
        self.data["im_active_power"] = self._decode_signed(registers[51])
        self.data["im_reactive_power"] = self._decode_signed(registers[52])
        self.data["im_power_factor"] = self._decode_signed(registers[53]) / 1000.0
        self.data["em_voltage"] = registers[69]
        self.data["em_freq"] = registers[70] / 10.0
        grid_power = self._decode_signed(registers[71])
        self.data["em_active_power"] = max(0, grid_power)
        self.data["em_active_power_returned"] = max(0, -grid_power)
        self.data["em_reactive_power"] = self._decode_signed(registers[72])

        return True
