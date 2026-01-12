"""Config flow for Niu Integration integration.
    Author: Giovanni P. (@pikka97)
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .api import NiuApi
from .const import *

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_SCOOTER_ID, default=DEFAULT_SCOOTER_ID): int,
    }
)


STEP_SENSORS_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSORS, default=AVAILABLE_SENSORS): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=AVAILABLE_SENSORS,
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
            ),
        ),
    }
)


class NiuAuthenticator:
    def __init__(self, username, password, scooter_id, sensors_selected) -> None:
        self.username = username
        self.password = password
        self.scooter_id = scooter_id
        self.sensors_selected = sensors_selected

    async def authenticate(self, hass):
        api = NiuApi(hass, self.username, self.password, self.scooter_id)
        try:
            token = await api.async_get_token()
            return token is not None
        except Exception:
            return None


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CanApp Integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Invoked when a user clicks the add button"""

        errors = {}

        if user_input != None:
            self._async_abort_entries_match({CONF_USERNAME: user_input[CONF_USERNAME]})

            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            scooter_id = user_input[CONF_SCOOTER_ID]

            # Validate credentials first; sensor selection comes next step
            niu_auth = NiuAuthenticator(username, password, scooter_id, [])
            auth_result = await niu_auth.authenticate(self.hass)
            if auth_result:
                self._credentials = {
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                    CONF_SCOOTER_ID: scooter_id,
                }
                return await self.async_step_sensors()
            
            # The user used wrong credentials...
            errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Second step: select sensors after successful login."""
        errors: dict[str, str] = {}

        if not hasattr(self, "_credentials"):
            return await self.async_step_user()

        if user_input != None:
            sensors_selected = user_input.get(CONF_SENSORS, [])
            if not sensors_selected:
                errors["base"] = "no_sensors"
            else:
                integration_title = "Niu EScooter Integration"
                niu_auth = NiuAuthenticator(
                    self._credentials[CONF_USERNAME],
                    self._credentials[CONF_PASSWORD],
                    self._credentials[CONF_SCOOTER_ID],
                    sensors_selected,
                )
                return self.async_create_entry(
                    title=integration_title, data={CONF_AUTH: niu_auth.__dict__}
                )

        return self.async_show_form(
            step_id="sensors", data_schema=STEP_SENSORS_DATA_SCHEMA, errors=errors
        )
