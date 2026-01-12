"""niu component."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_AUTH, CONF_SENSORS, DOMAIN, SENSOR_TYPE_BAT, SENSOR_TYPE_MOTO, SENSOR_TYPE_POS, SENSOR_TYPE_DIST, SENSOR_TYPE_OVERALL, SENSOR_TYPE_TRACK
from .api import NiuApi

_LOGGER = logging.getLogger(__name__)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Niu Smart Plug from a config entry."""

    niu_auth = entry.data.get(CONF_AUTH, None)
    if niu_auth == None:
        return False

    sensors_selected = niu_auth[CONF_SENSORS]
    if len(sensors_selected) < 1:
        _LOGGER.error("You did NOT selected any sensor... cant setup the integration..")
        return False

    if "LastTrackThumb" in sensors_selected:
        PLATFORMS.append("camera")

    username = niu_auth["username"]
    password = niu_auth["password"]
    scooter_id = niu_auth["scooter_id"]

    # Create API instance
    api = NiuApi(hass, username, password, scooter_id)

    # Initialize API asynchronously
    await api.async_init()

    # Create data update coordinator
    coordinator = NiuDataUpdateCoordinator(hass, api=api)
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
        "sensors_selected": sensors_selected,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if unload_ok:
            hass.data[DOMAIN].pop(entry.entry_id)
            if not hass.data[DOMAIN]:
                hass.data.pop(DOMAIN)
        return unload_ok
    return False


class NiuDataUpdateCoordinator(DataUpdateCoordinator):
    """Data update coordinator for Niu Scooters."""

    def __init__(self, hass: HomeAssistant, api: NiuApi) -> None:
        """Initialize the coordinator."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        _LOGGER.debug("Updating Niu Scooter data")

        # Update all data from API
        await self.api.async_update_bat()
        await self.api.async_update_moto()
        await self.api.async_update_moto_info()
        await self.api.async_update_track_info()

        # Return all sensor data in a structured format
        return {
            SENSOR_TYPE_BAT: {
                "batteryCharging": self.api.getDataBat("batteryCharging"),
                "isConnected": self.api.getDataBat("isConnected"),
                "chargedTimes": self.api.getDataBat("chargedTimes"),
                "temperatureDesc": self.api.getDataBat("temperatureDesc"),
                "temperature": self.api.getDataBat("temperature"),
                "gradeBattery": self.api.getDataBat("gradeBattery"),
                "bmsId": self.api.getDataBat("bmsId"),
            },
            SENSOR_TYPE_MOTO: {
                "nowSpeed": self.api.getDataMoto("nowSpeed"),
                "isConnected": self.api.getDataMoto("isConnected"),
                "isCharging": self.api.getDataMoto("isCharging"),
                "lockStatus": self.api.getDataMoto("lockStatus"),
                "leftTime": self.api.getDataMoto("leftTime"),
                "estimatedMileage": self.api.getDataMoto("estimatedMileage"),
                "centreCtrlBattery": self.api.getDataMoto("centreCtrlBattery"),
                "hdop": self.api.getDataMoto("hdop"),
            },
            SENSOR_TYPE_POS: {
                "lat": self.api.getDataPos("lat"),
                "lng": self.api.getDataPos("lng"),
            },
            SENSOR_TYPE_DIST: {
                "distance": self.api.getDataDist("distance"),
                "ridingTime": self.api.getDataDist("ridingTime"),
                "time": self.api.getDataDist("time"),
            },
            SENSOR_TYPE_OVERALL: {
                "totalMileage": self.api.getDataOverall("totalMileage"),
                "bindDaysCount": self.api.getDataOverall("bindDaysCount"),
            },
            SENSOR_TYPE_TRACK: {
                "startTime": self.api.getDataTrack("startTime"),
                "endTime": self.api.getDataTrack("endTime"),
                "distance": self.api.getDataTrack("distance"),
                "avespeed": self.api.getDataTrack("avespeed"),
                "ridingtime": self.api.getDataTrack("ridingtime"),
                "track_thumb": self.api.getDataTrack("track_thumb"),
            },
            "sn": self.api.sn,
            "sensor_prefix": self.api.sensor_prefix,
        }
