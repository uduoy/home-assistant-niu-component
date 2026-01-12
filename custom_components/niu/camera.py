"""Last Track for Niu Integration integration.
    Author: Giovanni P. (@pikka97)
"""
import logging
from typing import final

import httpx

from homeassistant.components.camera import CameraState
from homeassistant.components.generic.camera import GenericCamera
from homeassistant.helpers.httpx_client import get_async_client

from .api import NiuApi
from .const import *

_LOGGER = logging.getLogger(__name__)
GET_IMAGE_TIMEOUT = 10


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    niu_auth = entry.data.get(CONF_AUTH, None)
    if niu_auth == None:
        _LOGGER.error(
            "The authenticator of your Niu integration is None.. can not setup the integration..."
        )
        return False

    # Get coordinator and api from hass.data
    coordinator_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = coordinator_data["coordinator"]
    api = coordinator_data["api"]

    # Validate SN before creating entities
    if not api.sn:
        _LOGGER.error("Cannot create camera entity: SN not available")
        return False

    camera_name = api.sensor_prefix + " Last Track Camera"

    entry = {
        "name": camera_name,
        "still_image_url": "",
        "stream_source": None,
        "authentication": "basic",
        "username": None,
        "password": None,
        "limit_refetch_to_url_change": False,
        "content_type": "image/jpeg",
        "framerate": 2,
        "verify_ssl": False,
    }
    async_add_entities([LastTrackCamera(hass, api, coordinator, entry, camera_name, camera_name)])


class LastTrackCamera(GenericCamera):
    _attr_has_entity_name = True
    _attr_translation_key = "last_track_camera"
    
    def __init__(self, hass, api, coordinator, device_info, identifier: str, title: str) -> None:
        if not api.sn:
            raise ValueError("Cannot create camera entity: SN not available")
        self._api = api
        self._coordinator = coordinator
        self._sn = api.sn
        super().__init__(hass, device_info, identifier, title)

    @property
    @final
    def state(self) -> str:
        """Return the camera state."""
        return CameraState.IDLE

    @property
    def is_on(self) -> bool:
        """Return true if on."""
        return self._last_image != b""

    @property
    def unique_id(self):
        return f"camera.niu_{self._sn}_last_track"

    @property
    def device_info(self):
        device_name = f"Niu Scooter {self._sn}"
        dev = {
            "identifiers": {("niu", self._sn)},
            "name": device_name,
            "manufacturer": "Niu",
            "model": 1.0,
        }
        return dev

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        if self._coordinator.data is None:
            return self._last_image

        last_track_url = self._coordinator.data.get(SENSOR_TYPE_TRACK, {}).get("track_thumb")
        if not last_track_url:
            _LOGGER.debug("No track_thumb URL available")
            return self._last_image

        if last_track_url == self._last_url and self._previous_image != b"":
            # The path image is the same as before so the image is the same:
            return self._previous_image

        try:
            async_client = get_async_client(self.hass, verify_ssl=self.verify_ssl)
            response = await async_client.get(
                last_track_url, auth=self._auth, timeout=GET_IMAGE_TIMEOUT
            )
            response.raise_for_status()
            self._last_image = response.content
        except httpx.TimeoutException:
            _LOGGER.error("Timeout getting camera image from %s", self._name)
            return self._last_image
        except (httpx.RequestError, httpx.HTTPStatusError) as err:
            _LOGGER.error("Error getting new camera image from %s: %s", self._name, err)
            return self._last_image

        self._last_url = last_track_url
        self._previous_image = self._last_image
        return self._last_image
