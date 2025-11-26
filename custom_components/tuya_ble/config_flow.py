"""Config flow for Tuya BLE integration."""

from __future__ import annotations

import logging
# import pycountry
from typing import Any

import voluptuous as vol
from tuya_iot import AuthType

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlowWithConfigEntry,
)
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import (
    CONF_ADDRESS,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowHandler, FlowResult

from homeassistant.components.tuya.const import (
    CONF_APP_TYPE,
    CONF_ENDPOINT,
    TUYA_RESPONSE_CODE,
    TUYA_RESPONSE_MSG,
    TUYA_RESPONSE_SUCCESS,
)
from .tuya_ble import SERVICE_UUID, TuyaBLEDeviceCredentials

from .const import (
    DOMAIN,
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_AUTH_TYPE,
    TUYA_SMART_APP,
    CONF_USER_CODE,
    CONF_TOKEN_INFO,
    CONF_TERMINAL_ID,
    TUYA_CLIENT_ID,
    TUYA_SCHEMA,
)
from .devices import TuyaBLEData, get_device_readable_name
from .cloud import HASSTuyaBLEDeviceManager

_LOGGER = logging.getLogger(__name__)


async def _try_openapi_with_token(
    manager: HASSTuyaBLEDeviceManager,
    user_input: dict[str, Any],
    errors: dict[str, str],
    placeholders: dict[str, Any],
) -> dict[str, Any] | None:
    """Try to validate OpenAPI access with QR token info and Access ID/Secret.

    We keep using tuya-iot OpenAPI to fetch BLE credentials, but authenticate the
    user via QR code. For OpenAPI calls we still need Access ID/Secret.
    """
    data = {
        CONF_ENDPOINT: user_input[CONF_ENDPOINT],
        CONF_AUTH_TYPE: AuthType.SMART_HOME,
        CONF_ACCESS_ID: user_input[CONF_ACCESS_ID],
        CONF_ACCESS_SECRET: user_input[CONF_ACCESS_SECRET],
        CONF_APP_TYPE: TUYA_SMART_APP,
        CONF_TOKEN_INFO: user_input[CONF_TOKEN_INFO],
    }

    response = await manager._login(data, True)
    if response and response.get(TUYA_RESPONSE_SUCCESS, False):
        return data

    errors["base"] = "login_error"
    if response:
        placeholders.update(
            {
                TUYA_RESPONSE_CODE: response.get(TUYA_RESPONSE_CODE),
                TUYA_RESPONSE_MSG: response.get(TUYA_RESPONSE_MSG),
            }
        )
    return None


def _show_user_form(
    flow: FlowHandler,
    user_input: dict[str, Any],
    errors: dict[str, str],
    placeholders: dict[str, Any],
) -> FlowResult:
    """Show the initial form to request Access ID/Secret and User Code."""
    return flow.async_show_form(
        step_id="user",
        data_schema=vol.Schema(
            {
                vol.Required(
                    CONF_ACCESS_ID, default=user_input.get(CONF_ACCESS_ID, "")
                ): str,
                vol.Required(
                    CONF_ACCESS_SECRET,
                    default=user_input.get(CONF_ACCESS_SECRET, ""),
                ): str,
                vol.Required(
                    CONF_USER_CODE, default=user_input.get(CONF_USER_CODE, "")
                ): str,
            }
        ),
        errors=errors,
        description_placeholders=placeholders,
    )


class TuyaBLEOptionsFlow(OptionsFlowWithConfigEntry):
    """Handle a Tuya BLE options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return await self.async_step_user(user_input)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Options: Start with QR user code + Access credentials."""
        errors: dict[str, str] = {}
        placeholders: dict[str, Any] = {}

        if user_input is None:
            user_input = {}
            user_input.update(self.config_entry.options)
            return _show_user_form(self, user_input, errors, placeholders)

        # Store temporarily to context for scan step
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN]["_options_user_input"] = user_input
        return await self.async_step_scan()

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Display QR code and finalize options with token."""
        errors: dict[str, str] = {}
        placeholders: dict[str, Any] = {}

        domain_data = self.hass.data.get(DOMAIN, {})
        base_input: dict[str, Any] = domain_data.get("_options_user_input", {})

        # Prepare login control and QR
        if "_qr_code" not in domain_data:
            # Import here to avoid static analysis error if lib not installed yet
            from tuya_sharing import LoginControl  # type: ignore
            login_control = LoginControl()
            try:
                response = await self.hass.async_add_executor_job(
                    login_control.qr_code, TUYA_CLIENT_ID, TUYA_SCHEMA, base_input.get(CONF_USER_CODE, "")
                )
            except Exception as exc:  # pragma: no cover - depends on external lib
                errors["base"] = "login_error"
                placeholders = {TUYA_RESPONSE_MSG: str(exc), TUYA_RESPONSE_CODE: "0"}
                return _show_user_form(self, base_input, errors, placeholders)

            if not response.get(TUYA_RESPONSE_SUCCESS, False):
                errors["base"] = "login_error"
                placeholders = {
                    TUYA_RESPONSE_MSG: response.get(TUYA_RESPONSE_MSG, "Unknown error"),
                    TUYA_RESPONSE_CODE: response.get(TUYA_RESPONSE_CODE, "0"),
                }
                return _show_user_form(self, base_input, errors, placeholders)

            domain_data["_login_control"] = login_control
            domain_data["_qr_code"] = response["result"]["qrcode"]
            self.hass.data[DOMAIN] = domain_data

        # If user submitted, try to retrieve result and finish
        if user_input is not None:
            # Type: ignore to avoid static checker errors for external lib types
            login_control = domain_data["_login_control"]  # type: ignore[assignment]
            qr_code: str = domain_data["_qr_code"]
            ret, info = await self.hass.async_add_executor_job(
                login_control.login_result,
                qr_code,
                TUYA_CLIENT_ID,
                base_input.get(CONF_USER_CODE, ""),
            )
            if not ret:
                # regenerate QR
                del domain_data["_qr_code"]
                return await self.async_step_scan()

            entry: TuyaBLEData | None = None
            dd = self.hass.data.get(DOMAIN)
            if dd:
                entry = dd.get(self.config_entry.entry_id)
            if entry:
                token_info = {
                    "t": info.get("t"),
                    "uid": info.get("uid"),
                    "expire_time": info.get("expire_time"),
                    "access_token": info.get("access_token"),
                    "refresh_token": info.get("refresh_token"),
                }
                login_data = {
                    CONF_ACCESS_ID: base_input.get(CONF_ACCESS_ID),
                    CONF_ACCESS_SECRET: base_input.get(CONF_ACCESS_SECRET),
                    CONF_ENDPOINT: info.get(CONF_ENDPOINT),
                    CONF_TOKEN_INFO: token_info,
                    CONF_TERMINAL_ID: info.get(CONF_TERMINAL_ID),
                    CONF_AUTH_TYPE: AuthType.SMART_HOME,
                }
                # Validate by attempting to build cache
                entry.manager.data.update(login_data)
                # Try to fetch a known device credentials to make sure tokens work (lazy check)
                await entry.manager.build_cache()
                return self.async_create_entry(
                    title=self.config_entry.title,
                    data=entry.manager.data,
                )

        # Show QR
        from homeassistant.helpers import selector

        return self.async_show_form(
            step_id="scan",
            data_schema=vol.Schema(
                {
                    vol.Optional("QR"): selector.QrCodeSelector(
                        config=selector.QrCodeSelectorConfig(
                            data=f"tuyaSmart--qrLogin?token={self.hass.data[DOMAIN]['_qr_code']}",
                            scale=5,
                            error_correction_level=selector.QrErrorCorrectionLevel.QUARTILE,
                        )
                    )
                }
            ),
        )


class TuyaBLEConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tuya BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}
        self._data: dict[str, Any] = {}
        self._manager: HASSTuyaBLEDeviceManager | None = None
        self._get_device_info_error = False

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        if self._manager is None:
            self._manager = HASSTuyaBLEDeviceManager(self.hass, self._data)
        self.context["title_placeholders"] = {
            "name": await get_device_readable_name(
                discovery_info,
                self._manager,
            )
        }
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial user step: request Access ID/Secret and User Code, then show QR."""
        errors: dict[str, str] = {}
        placeholders: dict[str, Any] = {}
        if user_input is None:
            user_input = {}
            return _show_user_form(self, user_input, errors, placeholders)

        # Save the inputs and proceed to QR scan
        self._data.update(user_input)
        return await self.async_step_scan()

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Display QR code and finalize login using QR method."""
        # Ensure manager
        if self._manager is None:
            self._manager = HASSTuyaBLEDeviceManager(self.hass, self._data)

        # On first entry to scan, create QR
        if "_qr_code" not in self._data:
            from tuya_sharing import LoginControl  # type: ignore
            login_control = LoginControl()
            try:
                response = await self.hass.async_add_executor_job(
                    login_control.qr_code,
                    TUYA_CLIENT_ID,
                    TUYA_SCHEMA,
                    self._data.get(CONF_USER_CODE, ""),
                )
            except Exception as exc:  # pragma: no cover
                return _show_user_form(
                    self,
                    self._data,
                    {"base": "login_error"},
                    {TUYA_RESPONSE_MSG: str(exc), TUYA_RESPONSE_CODE: "0"},
                )

            if not response.get(TUYA_RESPONSE_SUCCESS, False):
                return _show_user_form(
                    self,
                    self._data,
                    {"base": "login_error"},
                    {
                        TUYA_RESPONSE_MSG: response.get(TUYA_RESPONSE_MSG, "Unknown error"),
                        TUYA_RESPONSE_CODE: response.get(TUYA_RESPONSE_CODE, "0"),
                    },
                )
            self._data["_login_control"] = login_control
            self._data["_qr_code"] = response["result"]["qrcode"]

        if user_input is not None:
            login_control = self._data["_login_control"]  # type: ignore[assignment]
            qr_code: str = self._data["_qr_code"]
            ret, info = await self.hass.async_add_executor_job(
                login_control.login_result,
                qr_code,
                TUYA_CLIENT_ID,
                self._data.get(CONF_USER_CODE, ""),
            )
            if not ret:
                del self._data["_qr_code"]
                return await self.async_step_scan()

            # Compose login data and validate with OpenAPI
            token_info = {
                "t": info.get("t"),
                "uid": info.get("uid"),
                "expire_time": info.get("expire_time"),
                "access_token": info.get("access_token"),
                "refresh_token": info.get("refresh_token"),
            }
            qr_login = {
                CONF_ENDPOINT: info.get(CONF_ENDPOINT),
                CONF_TOKEN_INFO: token_info,
                CONF_TERMINAL_ID: info.get(CONF_TERMINAL_ID),
            }

            # Merge Access ID/Secret supplied in user step
            qr_login[CONF_ACCESS_ID] = self._data.get(CONF_ACCESS_ID)
            qr_login[CONF_ACCESS_SECRET] = self._data.get(CONF_ACCESS_SECRET)

            validated = await _try_openapi_with_token(
                self._manager, qr_login, {}, {}
            )
            if validated:
                self._data.update(validated)
                return await self.async_step_device()

        # Show QR
        from homeassistant.helpers import selector

        return self.async_show_form(
            step_id="scan",
            data_schema=vol.Schema(
                {
                    vol.Optional("QR"): selector.QrCodeSelector(
                        config=selector.QrCodeSelectorConfig(
                            data=f"tuyaSmart--qrLogin?token={self._data['_qr_code']}",
                            scale=5,
                            error_correction_level=selector.QrErrorCorrectionLevel.QUARTILE,
                        )
                    )
                }
            ),
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            discovery_info = self._discovered_devices[address]
            local_name = await get_device_readable_name(discovery_info, self._manager)
            await self.async_set_unique_id(
                discovery_info.address, raise_on_progress=False
            )
            self._abort_if_unique_id_configured()
            credentials = await self._manager.get_device_credentials(
                discovery_info.address, self._get_device_info_error, True
            )
            self._data[CONF_ADDRESS] = discovery_info.address
            if credentials is None:
                self._get_device_info_error = True
                errors["base"] = "device_not_registered"
            else:
                return self.async_create_entry(
                    title=local_name,
                    data={CONF_ADDRESS: discovery_info.address},
                    options=self._data,
                )

        if discovery := self._discovery_info:
            self._discovered_devices[discovery.address] = discovery
        else:
            current_addresses = self._async_current_ids()
            for discovery in async_discovered_service_info(self.hass):
                if (
                    discovery.address in current_addresses
                    or discovery.address in self._discovered_devices
                    or discovery.service_data is None
                    or not SERVICE_UUID in discovery.service_data.keys()
                ):
                    continue
                self._discovered_devices[discovery.address] = discovery

        if not self._discovered_devices:
            return self.async_abort(reason="no_unconfigured_devices")

        def_address: str
        if user_input:
            def_address = user_input.get(CONF_ADDRESS)
        else:
            def_address = list(self._discovered_devices)[0]

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ADDRESS,
                        default=def_address,
                    ): vol.In(
                        {
                            service_info.address: await get_device_readable_name(
                                service_info,
                                self._manager,
                            )
                            for service_info in self._discovered_devices.values()
                        }
                    ),
                },
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> TuyaBLEOptionsFlow:
        """Get the options flow for this handler."""
        return TuyaBLEOptionsFlow(config_entry)
