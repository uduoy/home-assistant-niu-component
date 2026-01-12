"""
    Support for Niu Scooters by Marcel Westra.
    Asynchronous version implementation by Giovanni P. (@pikka97)
"""
import logging

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import *
from .api import NiuApi

_LOGGER = logging.getLogger(__name__)


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

    # add sensors
    devices = []
    for sensor in sensors_selected:
        if sensor != "LastTrackThumb":
            sensor_config = SENSOR_TYPES[sensor]
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

    async_add_entities(devices)
    return True


class NiuSensor(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        api: NiuApi,
        entry_id,
        name, # This 'name' parameter (from AVAILABLE_SENSORS) is no longer used for the entity name
        sensor_id,
        uom,
        id_name,
        sensor_grp,
        sensor_prefix, # This is also no longer directly used for the entity name
        device_class,
        sn,
        icon,
    ):
        self._unique_id = "sensor.niu_scooter_" + sn + "_" + sensor_id
        # self._name = (
        #     "NIU Scooter " + sensor_prefix + " " + name
        # )  # Scooter name as sensor prefix - REMOVED
        self._uom = uom
        self._api = api
        self._device_class = device_class
        self._id_name = id_name  # info field for parsing the URL
        self._sensor_grp = sensor_grp  # info field for choosing the right URL
        self._icon = icon
        self._state = 0
        self._attr_translation_key = sensor_id # Use sensor_id for translation
        super().__init__(coordinator)

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
        if self.coordinator.data is None:
            return self._state

        try:
            return self.coordinator.data[self._sensor_grp][self._id_name]
        except (KeyError, TypeError):
            return self._state

    @property
    def device_class(self):
        return self._device_class

    @property
    def device_info(self):
        device_name = "Niu E-scooter"
        return {
            "identifiers": {("niu", device_name)},
            "name": device_name,
            "manufacturer": "Niu",
            "model": 1.0,
        }

    @property
    def extra_state_attributes(self):
        if self._sensor_grp == SENSOR_TYPE_MOTO and self._id_name == "isConnected":
            if self.coordinator.data is None:
                return {}

            try:
                return {
                    "bmsId": self.coordinator.data[SENSOR_TYPE_BAT].get("bmsId"),
                    "latitude": self.coordinator.data[SENSOR_TYPE_POS].get("lat"),
                    "longitude": self.coordinator.data[SENSOR_TYPE_POS].get("lng"),
                    "time": self.coordinator.data[SENSOR_TYPE_DIST].get("time"),
                    "range": self.coordinator.data[SENSOR_TYPE_MOTO].get("estimatedMileage"),
                    "battery": self.coordinator.data[SENSOR_TYPE_BAT].get("batteryCharging"),
                    "battery_grade": self.coordinator.data[SENSOR_TYPE_BAT].get("gradeBattery"),
                    "centre_ctrl_batt": self.coordinator.data[SENSOR_TYPE_MOTO].get("centreCtrlBattery"),
                }
            except (KeyError, TypeError):
                return {}

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success
