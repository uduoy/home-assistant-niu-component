from __future__ import annotations

import asyncio
from datetime import datetime
import hashlib
import json
import logging
import ssl
from time import gmtime, strftime
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import ClientTimeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import *

_LOGGER = logging.getLogger(__name__)


class NiuApi:
    def __init__(self, hass, username: str, password: str, scooter_id: int) -> None:
        self.hass = hass
        self.username = username
        self.password = password
        self.scooter_id = int(scooter_id)

        self.dataBat: Optional[Dict[str, Any]] = None
        self.dataMoto: Optional[Dict[str, Any]] = None
        self.dataMotoInfo: Optional[Dict[str, Any]] = None
        self.dataTrackInfo: Optional[Dict[str, Any]] = None
        
        self.token: str = ""
        self.sn: str = ""
        self.sensor_prefix: str = ""

    async def async_init(self) -> None:
        """Initialize API asynchronously."""
        self.token = await self.async_get_token()
        
        if not self.token:
            _LOGGER.error("Failed to get authentication token")
            return
            
        api_uri = MOTOINFO_LIST_API_URI
        vehicles_info = await self.async_get_vehicles_info(api_uri)
        
        if not vehicles_info:
            _LOGGER.error("Failed to get vehicles info")
            return
            
        items = vehicles_info.get("data", {}).get("items", [])
        if not items or len(items) <= self.scooter_id:
            _LOGGER.error("Scooter ID %d not found in vehicles list", self.scooter_id)
            return
            
        self.sn = items[self.scooter_id].get("sn_id", "")
        self.sensor_prefix = items[self.scooter_id].get("scooter_name", "")
        
        if not self.sn:
            _LOGGER.error("Failed to get scooter SN")
            return

    async def async_get_token(self) -> str:
        """Get authentication token asynchronously."""
        url = ACCOUNT_BASE_URL + LOGIN_URI
        md5 = hashlib.md5(self.password.encode("utf-8")).hexdigest()
        data = {
            "account": self.username,
            "password": md5,
            "grant_type": "password",
            "scope": "base",
            "app_id": "niu_ktdrr960",
        }
        
        try:
            session = async_get_clientsession(self.hass, verify_ssl=False)
            async with session.post(url, data=data, timeout=ClientTimeout(total=10)) as response:
                if response.status != 200:
                    _LOGGER.error("Login failed with status %d", response.status)
                    return None
                    
                response_text = await response.text()
                token_data = json.loads(response_text)
                return token_data.get("data", {}).get("token", {}).get("access_token", "")
                
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as err:
            _LOGGER.error("Error getting token: %s", err)
            return None

    async def async_get_vehicles_info(self, path: str) -> Optional[Dict[str, Any]]:
        """Get vehicles information asynchronously."""
        if not self.token:
            _LOGGER.error("No token available")
            return None
            
        url = API_BASE_URL + path
        headers = {"token": str(self.token)}
        
        try:
            session = async_get_clientsession(self.hass, verify_ssl=False)
            async with session.get(url, headers=headers, timeout=ClientTimeout(total=10)) as response:
                if response.status != 200:
                    _LOGGER.debug("Vehicles info request failed with status %d", response.status)
                    return None
                    
                response_text = await response.text()
                return json.loads(response_text)
                
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as err:
            _LOGGER.debug("Error getting vehicles info: %s", err)
            return None

    async def async_get_info(self, path: str) -> Optional[Dict[str, Any]]:
        """Get information asynchronously."""
        if not self.token or not self.sn:
            _LOGGER.debug("No token or SN available")
            return None
            
        url = API_BASE_URL + path
        params = {"sn": self.sn}
        headers = {
            "token": str(self.token),
            "user-agent": "manager/4.10.4 (android; IN2020 11);lang=zh-CN;clientIdentifier=Domestic;timezone=Asia/Shanghai;model=IN2020;deviceName=IN2020;ostype=android",
        }
        
        try:
            session = async_get_clientsession(self.hass, verify_ssl=False)
            async with session.get(url, headers=headers, params=params, timeout=ClientTimeout(total=10)) as response:
                if response.status != 200:
                    _LOGGER.debug("Get info request failed with status %d", response.status)
                    return None
                    
                response_text = await response.text()
                data = json.loads(response_text)
                if data.get("status") != 0:
                    _LOGGER.debug("API returned non-zero status: %d", data.get("status"))
                    return None
                return data
                
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as err:
            _LOGGER.debug("Error getting info: %s", err)
            return None

    async def async_post_info(self, path: str) -> Optional[Dict[str, Any]]:
        """POST information asynchronously."""
        if not self.token or not self.sn:
            _LOGGER.debug("No token or SN available")
            return None
            
        url = API_BASE_URL + path
        headers = {"token": str(self.token), "Accept-Language": "en-US"}
        
        try:
            session = async_get_clientsession(self.hass, verify_ssl=False)
            async with session.post(url, headers=headers, data={"sn": self.sn}, timeout=ClientTimeout(total=10)) as response:
                if response.status != 200:
                    _LOGGER.debug("Post info request failed with status %d", response.status)
                    return None
                    
                response_text = await response.text()
                data = json.loads(response_text)
                if data.get("status") != 0:
                    _LOGGER.debug("API returned non-zero status: %d", data.get("status"))
                    return None
                return data
                
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as err:
            _LOGGER.debug("Error posting info: %s", err)
            return None

    async def async_post_info_track(self, path: str) -> Optional[Dict[str, Any]]:
        """POST track information asynchronously."""
        if not self.token or not self.sn:
            _LOGGER.debug("No token or SN available")
            return None
            
        url = API_BASE_URL + path
        headers = {
            "token": str(self.token),
            "Accept-Language": "en-US",
            "User-Agent": "manager/1.0.0 (identifier);clientIdentifier=identifier",
        }
        
        try:
            session = async_get_clientsession(self.hass, verify_ssl=False)
            async with session.post(
                url, 
                headers=headers, 
                json={"index": "0", "pagesize": 10, "sn": self.sn},
                timeout=ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    _LOGGER.debug("Track info request failed with status %d", response.status)
                    return None
                    
                response_text = await response.text()
                data = json.loads(response_text)
                if data.get("status") != 0:
                    _LOGGER.debug("API returned non-zero status: %d", data.get("status"))
                    return None
                return data
                
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as err:
            _LOGGER.debug("Error posting track info: %s", err)
            return None

    def getDataBat(self, id_field: str) -> Any:
        """Get battery data."""
        if not isinstance(self.dataBat, dict):
            return None
        try:
            return self.dataBat.get("data", {}).get("batteries", {}).get("compartmentA", {}).get(id_field)
        except (KeyError, TypeError):
            return None

    def getDataMoto(self, id_field: str) -> Any:
        """Get motor data."""
        if not isinstance(self.dataMoto, dict):
            return None
        try:
            return self.dataMoto.get("data", {}).get(id_field)
        except (KeyError, TypeError):
            return None

    def getDataDist(self, id_field: str) -> Any:
        """Get distance data."""
        if not isinstance(self.dataMoto, dict):
            return None
        try:
            return self.dataMoto.get("data", {}).get("lastTrack", {}).get(id_field)
        except (KeyError, TypeError):
            return None

    def getDataPos(self, id_field: str) -> Any:
        """Get position data."""
        if not isinstance(self.dataMoto, dict):
            return None
        try:
            return self.dataMoto.get("data", {}).get("postion", {}).get(id_field)
        except (KeyError, TypeError):
            return None

    def getDataOverall(self, id_field: str) -> Any:
        """Get overall data."""
        if not isinstance(self.dataMotoInfo, dict):
            return None
        try:
            return self.dataMotoInfo.get("data", {}).get(id_field)
        except (KeyError, TypeError):
            return None

    def getDataTrack(self, id_field: str) -> Any:
        """Get track data."""
        if not isinstance(self.dataTrackInfo, dict):
            return None
        try:
            if id_field == "startTime" or id_field == "endTime":
                timestamp = self.dataTrackInfo.get("data", [{}])[0].get(id_field, 0)
                if timestamp:
                    return datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
                return None
            if id_field == "ridingtime":
                seconds = self.dataTrackInfo.get("data", [{}])[0].get(id_field, 0)
                if seconds:
                    return strftime("%H:%M:%S", gmtime(seconds))
                return None
            if id_field == "track_thumb":
                thumburl = self.dataTrackInfo.get("data", [{}])[0].get(id_field, "")
                if thumburl:
                    thumburl = thumburl.replace("app-api.niucache.com", "app-api.niu.com")
                    return thumburl.replace("/track/thumb/", "/track/overseas/thumb/")
                return None
            return self.dataTrackInfo.get("data", [{}])[0].get(id_field)
        except (KeyError, TypeError, IndexError):
            return None

    async def async_update_bat(self) -> None:
        """Update battery information asynchronously."""
        self.dataBat = await self.async_get_info(MOTOR_BATTERY_API_URI)

    async def async_update_moto(self) -> None:
        """Update motor information asynchronously."""
        self.dataMoto = await self.async_get_info(MOTOR_INDEX_API_URI)

    async def async_update_moto_info(self) -> None:
        """Update motor overall information asynchronously."""
        self.dataMotoInfo = await self.async_post_info(MOTOINFO_ALL_API_URI)

    async def async_update_track_info(self) -> None:
        """Update track information asynchronously."""
        self.dataTrackInfo = await self.async_post_info_track(TRACK_LIST_API_URI)