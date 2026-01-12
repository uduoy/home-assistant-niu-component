"""
    Support for Niu Scooters by Marcel Westra.
    Asynchronous version implementation by Giovanni P. (@pikka97)
"""
import logging
import re

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import *
from .api import NiuApi

_LOGGER = logging.getLogger(__name__)


def _generate_entity_id(sensor_prefix: str | None, sn: str | None, sensor_name: str, sensor_id: str | None) -> str:
    """Build a deterministic entity_id using scooter name and sensor key."""
    device_source = sensor_prefix or sn or "niu_scooter"
    slug_device = slugify(device_source) or "niu_scooter"

    # Prefer CamelCase sensor name, fallback to snake_case id and generic label
    name_source = sensor_name or sensor_id or "sensor"
    camel_to_snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name_source)
    slug_sensor = slugify(camel_to_snake or name_source) or "sensor"

    return f"sensor.{slug_device}_{slug_sensor}"


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    niu_auth = entry.data.get(CONF_AUTH, None)
    if niu_auth == None:
        _LOGGER.error(
            "The authenticator of your Niu integration is None.. can not setup the integration..."
        )
        return False

    sensors_selected = niu_auth[CONF_SENSORS]

    # Get coordinator and api from hass.data
    coordinator_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = coordinator_data["coordinator"]
    api = coordinator_data["api"]
    
    _LOGGER.debug("Setting up sensors: sn=%s, sensor_prefix=%s", api.sn, api.sensor_prefix)

    # Validate SN before creating entities
    if not api.sn or api.sn.lower() == "none":
        _LOGGER.error("Cannot create sensor entities: SN not available or invalid (sn=%s)", api.sn)
        return False

    entity_registry = er.async_get(hass)

    # add sensors
    devices = []
    for sensor in sensors_selected:
        if sensor != "LastTrackThumb":
            sensor_config = SENSOR_TYPES[sensor]
            desired_entity_id = _generate_entity_id(
                api.sensor_prefix,
                api.sn,
                sensor,
                sensor_config[0],
            )
            unique_id = f"sensor.niu_{api.sn}_{sensor}"

            current_entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            if current_entity_id and current_entity_id != desired_entity_id:
                try:
                    entity_registry.async_update_entity(
                        current_entity_id,
                        new_entity_id=desired_entity_id,
                    )
                    _LOGGER.debug(
                        "Renamed entity %s -> %s for sensor %s",
                        current_entity_id,
                        desired_entity_id,
                        sensor,
                    )
                except ValueError:
                    _LOGGER.warning(
                        "Unable to rename entity %s to %s (already in use)",
                        current_entity_id,
                        desired_entity_id,
                    )

            devices.append(
                NiuSensor(
                    coordinator,
                    api,
                    entry.entry_id,
                    sensor,
                    sensor_config[0],
                    sensor_config[1],
                    sensor_config[2],
                    sensor_config[3],
                    api.sensor_prefix,
                    sensor_config[4],
                    api.sn,
                    sensor_config[5],
                )
            )
        else:
            # Last Track Thumb sensor will be used as camera... now just skip it
            pass

    # Always add vehicle metadata sensors (diagnostic). These are stable and useful
    # for UI clarity without cluttering the primary sensor list.
    devices.extend(
        [
            NiuVehicleInfoSensor(coordinator, api, "sku_name", "SkuName"),
            NiuVehicleInfoSensor(coordinator, api, "product_type", "ProductType"),
            NiuVehicleInfoSensor(coordinator, api, "carframe_id", "CarframeId"),
        ]
    )

    async_add_entities(devices)
    return True


class NiuVehicleInfoSensor(CoordinatorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, api: NiuApi, key: str, label: str) -> None:
        super().__init__(coordinator)
        self._api = api
        self._sn = api.sn
        self._key = key
        self._label = label

        self._attr_translation_key = key
        self._attr_unique_id = f"sensor.niu_{self._sn}_{key}"
        self.entity_id = _generate_entity_id(api.sensor_prefix, api.sn, label, key)

    @property
    def state(self):
        return getattr(self._api, self._key, None)

    @property
    def device_info(self):
        device_name = self._api.sensor_prefix if self._api.sensor_prefix else f"Niu Scooter {self._sn}"
        identifier = self._sn if self._sn and self._sn.lower() != "none" else device_name
        return {
            "identifiers": {(DOMAIN, identifier)},
            "name": device_name,
            "manufacturer": "Niu",
            "model": self._api.sku_name or self._api.product_type or "Niu Scooter",
            "hw_version": self._api.product_type,
            "serial_number": self._api.carframe_id,
        }


class NiuSensor(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        api: NiuApi,
        entry_id,
        name, # This 'name' parameter (from AVAILABLE_SENSORS) is used as sensor_name for unique_id
        sensor_id,
        uom,
        id_name,
        sensor_grp,
        sensor_prefix, # This is also no longer directly used for the entity name
        device_class,
        sn,
        icon,
    ):
        if not sn or sn.lower() == "none":
            raise ValueError(f"Invalid SN provided for sensor {name}")
        self._sn = sn
        self._sensor_name = name  # e.g., "TimesCharged"
        self._unique_id = f"sensor.niu_{sn}_{name}"
        _LOGGER.debug("Creating sensor: unique_id=%s, sn=%s, name=%s", self._unique_id, sn, name)
        # self._name = (
        #     "NIU Scooter " + sensor_prefix + " " + name
        # )  # Scooter name as sensor prefix - REMOVED
        self._uom = uom
        self._api = api
        self._device_class = device_class
        self._id_name = id_name  # info field for parsing the URL
        self._sensor_grp = sensor_grp  # info field for choosing the right URL
        self._icon = icon
        self._state = None
        self._raw_state = None
        self._last_valid_state = None
        self._attr_translation_key = sensor_id # Use sensor_id for translation (lowercase with underscores)

        # UI grouping: keep key day-to-day metrics in the main list, push noisy/secondary
        # details (GPS precision/lat/lng/connectivity/track internals) into Diagnostics.
        diagnostic_sensors = {
            "Isconnected",
            "ScooterConnected",
            "HDOP",
            "Longitude",
            "Latitude",
            "temperatureDesc",
            "Distance",
            "RidingTime",
            "LastTrackStartTime",
            "LastTrackEndTime",
            "LastTrackRidingtime",
        }
        if name in diagnostic_sensors:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self.entity_id = _generate_entity_id(sensor_prefix, sn, name, sensor_id)
        super().__init__(coordinator)

    def _handle_coordinator_update(self) -> None:
        raw_value = None
        if self.coordinator.data is not None:
            raw_value = self.coordinator.data.get(self._sensor_grp, {}).get(self._id_name)

        self._raw_state = raw_value

        if raw_value is not None:
            self._last_valid_state = raw_value
            self._state = raw_value
        elif self._last_valid_state is not None:
            # Keep last known good value when server returns null
            self._state = self._last_valid_state
        else:
            self._state = None

        self.async_write_ha_state()

    @property
    def unique_id(self):
        return self._unique_id

    # @property
    # def name(self):
    #     return self._name # REMOVED - Handled by translation_key and _attr_has_entity_name

    @property
    def unit_of_measurement(self):
        return self._uom

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        return self._state

    @property
    def device_class(self):
        return self._device_class

    @property
    def device_info(self):
        # Use sensor_prefix (scooter name) if available, otherwise use SN
        device_name = self._api.sensor_prefix if self._api.sensor_prefix else f"Niu Scooter {self._sn}"
        # Use SN as primary identifier, fallback to device_name
        identifier = self._sn if self._sn and self._sn.lower() != "none" else device_name
        return {
            "identifiers": {("niu", identifier)},
            "name": device_name,
            "manufacturer": "Niu",
            "model": self._api.sku_name or self._api.product_type or "Niu Scooter",
            "hw_version": self._api.product_type,
            "serial_number": self._api.carframe_id,
        }

    @property
    def extra_state_attributes(self):
        raw_value = self._raw_state
        value_source = "live" if raw_value is not None else ("cached" if self._state is not None else "none")

        attrs = {
            "raw_value": raw_value,
            "value_source": value_source,
        }

        # Keep existing extra attributes for connectivity sensor
        if self._sensor_grp == SENSOR_TYPE_MOTO and self._id_name == "isConnected":
            if self.coordinator.data is None:
                return attrs
            
            attrs.update({
                "bmsId": self.coordinator.data.get(SENSOR_TYPE_BAT, {}).get("bmsId"),
                "latitude": self.coordinator.data.get(SENSOR_TYPE_POS, {}).get("lat"),
                "longitude": self.coordinator.data.get(SENSOR_TYPE_POS, {}).get("lng"),
                "time": self.coordinator.data.get(SENSOR_TYPE_DIST, {}).get("time"),
                "range": self.coordinator.data.get(SENSOR_TYPE_BAT, {}).get("estimatedMileage")
                or self.coordinator.data.get(SENSOR_TYPE_MOTO, {}).get("estimatedMileage"),
                "battery": self.coordinator.data.get(SENSOR_TYPE_BAT, {}).get("batteryCharging"),
                "battery_grade": self.coordinator.data.get(SENSOR_TYPE_BAT, {}).get("gradeBattery"),
                "centre_ctrl_batt": self.coordinator.data.get(SENSOR_TYPE_BAT, {}).get("centreCtrlBattery")
                or self.coordinator.data.get(SENSOR_TYPE_MOTO, {}).get("centreCtrlBattery"),
            })
        return attrs

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success
