"""The Tuya BLE integration."""
from __future__ import annotations

from dataclasses import dataclass, field

import logging
from typing import Callable

from homeassistant.components.button import (
    ButtonEntityDescription,
    ButtonEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)


TuyaBLEButtonIsAvailable = Callable[["TuyaBLEButton", TuyaBLEProductInfo], bool] | None
TuyaBLEActionButtonIsAvailable = (
    Callable[["TuyaBLEActionButton", TuyaBLEProductInfo], bool] | None
)


@dataclass
class TuyaBLEActionButtonMapping:
    description: ButtonEntityDescription
    action: Callable[[TuyaBLEDevice], Awaitable]
    is_available: TuyaBLEActionButtonIsAvailable = None


@dataclass
class TuyaBLEButtonMapping:
    dp_id: int
    description: ButtonEntityDescription
    force_add: bool = True
    dp_type: TuyaBLEDataPointType | None = None
    is_available: TuyaBLEButtonIsAvailable = None


def is_fingerbot_in_push_mode(self: TuyaBLEButton, product: TuyaBLEProductInfo) -> bool:
    result: bool = True
    if product.fingerbot:
        datapoint = self._device.datapoints[product.fingerbot.mode]
        if datapoint:
            result = datapoint.value == 0
    return result


@dataclass
class TuyaBLEFingerbotModeMapping(TuyaBLEButtonMapping):
    description: ButtonEntityDescription = field(
        default_factory=lambda: ButtonEntityDescription(
            key="push",
        )
    )
    is_available: TuyaBLEButtonIsAvailable = is_fingerbot_in_push_mode

@dataclass
class TuyaBLELockMapping(TuyaBLEButtonMapping):
    description: ButtonEntityDescription = field(
        default_factory=lambda: ButtonEntityDescription(
            key="push",
        )
    )
    is_available: TuyaBLEButtonIsAvailable = 0

@dataclass
class TuyaBLECategoryButtonMapping:
    products: dict[str, list[TuyaBLEButtonMapping]] | None = None
    mapping: list[TuyaBLEButtonMapping] | None = None


mapping: dict[str, TuyaBLECategoryButtonMapping] = {
    "szjqr": TuyaBLECategoryButtonMapping(
        products={
            **dict.fromkeys(
                ["3yqdo5yt", "xhf790if"],  # CubeTouch 1s and II
                [
                    TuyaBLEFingerbotModeMapping(dp_id=1),
                ],
            ),
            **dict.fromkeys(
                [
                    "blliqpsj",
                    "ndvkgsrm",
                    "yiihr7zh",
                    "neq16kgd"
                ],  # Fingerbot Plus
                [
                    TuyaBLEFingerbotModeMapping(dp_id=2),
                ],
            ),
            **dict.fromkeys(
                [
                    "ltak7e1p",
                    "y6kttvd6",
                    "yrnk7mnn",
                    "nvr2rocq",
                    "bnt7wajf",
                    "rvdceqjh",
                    "5xhbk964",
                ],  # Fingerbot
                [
                    TuyaBLEFingerbotModeMapping(dp_id=2),
                ],
            ),
        },
    ),
    "kg": TuyaBLECategoryButtonMapping(
        products={
            **dict.fromkeys(
                [
                    "mknd4lci",
                    "riecov42"
                ],  # Fingerbot Plus
                [
                    TuyaBLEFingerbotModeMapping(dp_id=108),
                ],
            ),
            # Fingerbot Touch (bs3ubslo): expose per-channel action buttons when in Push mode
            "bs3ubslo": [
                TuyaBLEButtonMapping(
                    dp_id=1,
                    description=ButtonEntityDescription(
                        key="action_1",
                        name="Action 1",
                    ),
                    # Available when channel 1 mode == push (0)
                    is_available=lambda self, product: (
                        (dp := self._device.datapoints[101]) is not None
                        and (dp.value if not isinstance(dp.value, bytes) else int.from_bytes(dp.value[:1], "big")) == 0
                    ),
                ),
                TuyaBLEButtonMapping(
                    dp_id=2,
                    description=ButtonEntityDescription(
                        key="action_2",
                        name="Action 2",
                    ),
                    # Available when channel 2 mode == push (0)
                    is_available=lambda self, product: (
                        (dp := self._device.datapoints[102]) is not None
                        and (dp.value if not isinstance(dp.value, bytes) else int.from_bytes(dp.value[:1], "big")) == 0
                    ),
                ),
            ],
        },
    ),
    "znhsb": TuyaBLECategoryButtonMapping(
        products={
            "cdlandip":  # Smart water bottle
            [
                TuyaBLEButtonMapping(
                    dp_id=109,
                    description=ButtonEntityDescription(
                        key="bright_lid_screen",
                    ),
                ),
            ],
        },
    ),
    "ms": TuyaBLECategoryButtonMapping(
          products={
             "okkyfgfs": # Smart Lock
             [
                 TuyaBLELockMapping(
                     dp_id=6,
                     description=ButtonEntityDescription(
                         key="bluetooth_unlock",
                     ),
                 ),
             ],
          },
      ),
}


def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLECategoryButtonMapping]:
    category = mapping.get(device.category)
    if category is not None and category.products is not None:
        product_mapping = category.products.get(device.product_id)
        if product_mapping is not None:
            return product_mapping
        if category.mapping is not None:
            return category.mapping
        else:
            return []
    else:
        return []


class TuyaBLEButton(TuyaBLEEntity, ButtonEntity):
    """Representation of a Tuya BLE Button."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLEButtonMapping,
    ) -> None:
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping

    def press(self) -> None:
        """Press the button."""
        datapoint = self._device.datapoints.get_or_create(
            self._mapping.dp_id,
            TuyaBLEDataPointType.DT_BOOL,
            False,
        )
        if datapoint:
            if getattr(self._product, "lock", False):  # Safely check if 'lock' exists and is True
                #Lock needs true to activate lock/unlock commands
                self._hass.create_task(datapoint.set_value(True))
            else:
                self._hass.create_task(datapoint.set_value(not bool(datapoint.value)))

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        result = super().available
        if result and self._mapping.is_available:
            result = self._mapping.is_available(self, self._product)
        return result


class TuyaBLEActionButton(TuyaBLEEntity, ButtonEntity):
    """Representation of a Tuya BLE Action Button."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLEActionButtonMapping,
    ) -> None:
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping

    def press(self) -> None:
        """Press the button."""
        self._hass.create_task(self._mapping.action(self._device))

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        result = super().available
        if result and self._mapping.is_available:
            result = self._mapping.is_available(self, self._product)
        return result


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE sensors."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    entities: list[TuyaBLEButton] = []

    for mapping in get_mapping_by_device(data.device):
        if mapping.force_add or data.device.datapoints.has_id(
            mapping.dp_id, mapping.dp_type
        ):
            entities.append(
                TuyaBLEButton(
                    hass,
                    data.coordinator,
                    data.device,
                    data.product,
                    mapping,
                )
            )

    action_mappings: list[TuyaBLEActionButtonMapping] = [
        TuyaBLEActionButtonMapping(
            description=ButtonEntityDescription(
                key="reconnect",
                entity_category=EntityCategory.DIAGNOSTIC,
                icon="mdi:restart",
            ),
            action=lambda device: device.reconnect(),
            is_available=lambda self, product: not self.device.connected,
        ),
        TuyaBLEActionButtonMapping(
            description=ButtonEntityDescription(
                key="reconnect_and_refresh",
                entity_category=EntityCategory.DIAGNOSTIC,
                icon="mdi:sync",
            ),
            action=lambda device: device.reconnect_and_update(),
            is_available=lambda self, product: not self.device.connected,
        ),
    ]
    for mapping in action_mappings:
        entities.append(
            TuyaBLEActionButton(
                hass,
                data.coordinator,
                data.device,
                data.product,
                mapping,
            )
        )

    async_add_entities(entities)
