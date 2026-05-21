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
        api = NiuApi.from_hass(hass, self.username, self.password, self.scooter_id)
        try:
            token = await api.async_get_token()
            if isinstance(token, bool):
                return token
            else:
                return token != ""
        except Exception as err:
            _LOGGER.error("Authentication failed: %s", err, exc_info=True)
            return False


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CanApp Integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Invoked when a user clicks the add button"""

        integration_title = "Niu EScooter Integration"
        errors = {}

        if user_input != None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            scooter_id = user_input[CONF_SCOOTER_ID]
            sensors_selected = user_input[CONF_SENSORS]
            niu_auth = NiuAuthenticator(
                username, password, scooter_id, sensors_selected
            )
            auth_result = await niu_auth.authenticate(self.hass)
            if auth_result:
                return self.async_create_entry(
                    title=integration_title, data={CONF_AUTH: niu_auth.__dict__}
                )
            else:
                # The user used wrong credentials...
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return NiuOptionsFlowHandler()


class NiuOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle NIU integration options."""

    async def async_step_init(self, user_input=None):
        """Manage the NIU options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=60,
                        unit_of_measurement="minutes",
                        mode=selector.NumberSelectorMode.BOX,
                    ),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
