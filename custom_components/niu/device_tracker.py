"""Device tracker platform for NIU scooters."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import NiuApi
from .const import DOMAIN, SENSOR_TYPE_POS, SENSOR_TYPE_TRACK, SENSOR_TYPE_BAT

_LOGGER = logging.getLogger(__name__)


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class NiuScooterTracker(CoordinatorEntity, TrackerEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "scooter_location"

    def __init__(self, coordinator, api: NiuApi) -> None:
        super().__init__(coordinator)
        self._api = api
        self._sn = api.sn

        self._attr_unique_id = f"device_tracker.niu_{self._sn}_location"

    @property
    def device_info(self):
        device_name = self._api.sensor_prefix if self._api.sensor_prefix else f"Niu Scooter {self._sn}"
        identifier = self._sn if self._sn and self._sn.lower() != "none" else device_name
        return {
            "identifiers": {(DOMAIN, identifier)},
            "name": device_name,
            "manufacturer": "Niu",
            "model": 1.0,
        }

    @property
    def latitude(self) -> float | None:
        # Prefer live position from motor_index_info
        if self.coordinator.data is not None:
            lat = self.coordinator.data.get(SENSOR_TYPE_POS, {}).get("lat")
            lat_f = _coerce_float(lat)
            if lat_f is not None:
                return lat_f

        # Fallback: last track lastPoint
        track_info = getattr(self._api, "dataTrackInfo", None)
        if isinstance(track_info, dict):
            try:
                lat = track_info.get("data", [{}])[0].get("lastPoint", {}).get("lat")
                return _coerce_float(lat)
            except (IndexError, AttributeError, TypeError):
                return None
        return None

    @property
    def longitude(self) -> float | None:
        # Prefer live position from motor_index_info
        if self.coordinator.data is not None:
            lng = self.coordinator.data.get(SENSOR_TYPE_POS, {}).get("lng")
            lng_f = _coerce_float(lng)
            if lng_f is not None:
                return lng_f

        # Fallback: last track lastPoint
        track_info = getattr(self._api, "dataTrackInfo", None)
        if isinstance(track_info, dict):
            try:
                lng = track_info.get("data", [{}])[0].get("lastPoint", {}).get("lng")
                return _coerce_float(lng)
            except (IndexError, AttributeError, TypeError):
                return None
        return None

    @property
    def source_type(self) -> str:
        return "gps"

    @property
    def extra_state_attributes(self):
        attrs: dict[str, Any] = {}

        lat = self.latitude
        lng = self.longitude
        if lat is None or lng is None:
            attrs["location_source"] = "none"
        else:
            # Determine source: if POSITION is present in parsed, treat as live
            if self.coordinator.data is not None:
                parsed_lat = self.coordinator.data.get(SENSOR_TYPE_POS, {}).get("lat")
                parsed_lng = self.coordinator.data.get(SENSOR_TYPE_POS, {}).get("lng")
                if _coerce_float(parsed_lat) is not None and _coerce_float(parsed_lng) is not None:
                    attrs["location_source"] = "live"
                else:
                    attrs["location_source"] = "last_track"

        if self.coordinator.data is not None:
            attrs["battery"] = self.coordinator.data.get(SENSOR_TYPE_BAT, {}).get("batteryCharging")
            attrs["last_track_start_time"] = self.coordinator.data.get(SENSOR_TYPE_TRACK, {}).get("startTime")
            attrs["last_track_end_time"] = self.coordinator.data.get(SENSOR_TYPE_TRACK, {}).get("endTime")

        # Keep standard attributes for maps
        if lat is not None:
            attrs[ATTR_LATITUDE] = lat
        if lng is not None:
            attrs[ATTR_LONGITUDE] = lng

        return attrs


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = coordinator_data["coordinator"]
    api: NiuApi = coordinator_data["api"]

    if not api.sn or api.sn.lower() == "none":
        _LOGGER.error("Cannot create device_tracker entity: SN not available or invalid (sn=%s)", api.sn)
        return

    async_add_entities([NiuScooterTracker(coordinator, api)])
