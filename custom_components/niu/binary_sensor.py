"""Binary sensor platform for NIU scooters.

Converts status fields (isConnected, isCharging, lockStatus) from plain
sensors into proper binary sensors with on/off semantics and device classes.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BIN_SENSOR_TYPES,
    CONF_AUTH,
    DOMAIN,
    SENSOR_TYPE_BAT,
    SENSOR_TYPE_MOTO,
    SENSOR_TYPE_POS,
)

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASS_MAP = {
    "battery_charging": BinarySensorDeviceClass.BATTERY_CHARGING,
    "connectivity": BinarySensorDeviceClass.CONNECTIVITY,
    "lock": BinarySensorDeviceClass.LOCK,
}


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up NIU binary sensors from a config entry."""
    coordinator_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = coordinator_data["coordinator"]
    api = coordinator_data["api"]

    if not api.sn:
        _LOGGER.error("Cannot create binary sensor entities: SN not available")
        return

    devices = []
    for sensor_key, config in BIN_SENSOR_TYPES.items():
        devices.append(NiuBinarySensor(coordinator, api, sensor_key, config))

    async_add_entities(devices)


class NiuBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for NIU status fields."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, api, sensor_key, config) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._api = api
        self._sn = api.sn
        self._sensor_key = sensor_key
        self._translation_key = config[0]
        self._id_name = config[1]
        self._sensor_grp = config[2]
        self._device_class = config[3]
        self._icon = config[4]

        self._attr_unique_id = f"binary_sensor.niu_{self._sn}_{sensor_key}"
        self._attr_translation_key = self._translation_key

        device_class = DEVICE_CLASS_MAP.get(self._device_class)
        if device_class:
            self._attr_device_class = device_class

    @property
    def icon(self):
        return self._icon

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._sensor_grp, {}).get(self._id_name)
        if raw is None:
            return None
        return bool(int(raw)) if raw else False

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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes for connectivity sensor."""
        if self._sensor_grp != SENSOR_TYPE_MOTO or self._id_name != "isConnected":
            return None
        if self.coordinator.data is None:
            return None

        return {
            "bmsId": self.coordinator.data.get(SENSOR_TYPE_BAT, {}).get("bmsId"),
            "latitude": self.coordinator.data.get(SENSOR_TYPE_POS, {}).get("lat"),
            "longitude": self.coordinator.data.get(SENSOR_TYPE_POS, {}).get("lng"),
            "time": self.coordinator.data.get("DIST", {}).get("time"),
            "range": (
                self.coordinator.data.get(SENSOR_TYPE_BAT, {}).get("estimatedMileage")
                or self.coordinator.data.get(SENSOR_TYPE_MOTO, {}).get("estimatedMileage")
            ),
            "battery": self.coordinator.data.get(SENSOR_TYPE_BAT, {}).get("batteryCharging"),
            "battery_grade": self.coordinator.data.get(SENSOR_TYPE_BAT, {}).get("gradeBattery"),
            "centre_ctrl_batt": (
                self.coordinator.data.get(SENSOR_TYPE_BAT, {}).get("centreCtrlBattery")
                or self.coordinator.data.get(SENSOR_TYPE_MOTO, {}).get("centreCtrlBattery")
            ),
        }
