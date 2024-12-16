""" Implements the Tuto HACS sensors component """
import logging
from datetime import datetime, timedelta
import async_timeout
import voluptuous as vol

import requests
import json

import urllib.parse


from homeassistant.const import UnitOfEnergy, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback, Event, State
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from homeassistant.helpers.event import (
    async_track_time_interval,
    async_track_state_change_event,
)

from homeassistant.helpers.device_registry import DeviceEntryType

from homeassistant.helpers.entity import DeviceInfo

import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    CONF_BATTERIE_VIRTUELLE_CURRENT_INDEX,
    CONF_BATTERIE_VIRTUELLE_TOTAL_INJECTION,
    CONF_BATTERIE_VIRTUELLE_LAST_UPDATE_DATE,
    CONF_DEVICE_NAME
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Configuration des entités sensor à partir de la configuration
    ConfigEntry passée en argument"""

    coordinator = USECoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    _LOGGER.debug("Calling async_setup_entry entry=%s", entry)
    entity1 = BatterieVirtuelleCurrentIndexEntity(hass, coordinator, entry)
    entity2 = BatterieVirtuelleTotalInjectionEntity(hass, coordinator, entry)
    entity3 = BatterieVirtuelleLastUpdateDateEntity(hass, coordinator, entry)
    async_add_entities([entity1, entity2, entity3], True)

    # Add services
    platform = async_get_current_platform()


class USECoordinator(DataUpdateCoordinator):
    _username: str
    _password: str

    def __init__(self, hass, entry: ConfigEntry):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="USE BV",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(hours=1),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=True
        )
        self._username = entry.data.get("username")
        self._password = safe_string = urllib.parse.quote_plus(
            entry.data.get("password"))

    async def _async_setup(self):
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        # self._device = await self.my_api.get_device()

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        async with async_timeout.timeout(10):
            return await self.hass.async_add_executor_job(self.blockingGetBV)

    def blockingGetBV(self):
        try:
            headers = {
                'Host': 'espace-client.urbansolar.energy',
                'accept': 'application/json, text/plain, */*',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept-Encoding': 'gzip, deflate, br',
                "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7,de;q=0.6",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "referrer": "https://espace-client.urbansolar.energy/connexion",
                "referrerPolicy": "strict-origin-when-cross-origin",
            }

            s = requests.session()

            req = s.get('https://espace-client.urbansolar.energy/api/login', headers=headers,
                        auth=(self._username, self._password))

            data = [{"operationName": "getUserWithBillingAccount", "variables": {},
                    "query": "query getUserWithBillingAccount {\n  me {\n    billingAccounts {\n      agreements {\n        bv {\n          currentCharge\n          totalInjection\n          startDate\n          updateDate\n          }\n        }\n      }\n    }\n}"}]

            req2 = s.post(
                "https://espace-client.urbansolar.energy/api/graphql", json=data)

            return json.loads(req2.text)[0]["data"]["me"]["billingAccounts"][0]["agreements"][0]["bv"]
        except Exception as e:
            _LOGGER.error(
                "Appel de _get_index_batterie_virtuelle en erreur : ", e)
            return None


class BatterieVirtuelleCurrentIndexEntity(CoordinatorEntity, SensorEntity):
    """La classe de l'entité TutoHacs"""
    _hass: HomeAssistant
    _username: str
    _password: str

    def __init__(
        self,
        hass: HomeAssistant,  # pylint: disable=unused-argument
        coordinator: USECoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        """Initisalisation de notre entité"""
        self._hass = hass
        self._attr_has_entity_name = True
        self._attr_name = CONF_BATTERIE_VIRTUELLE_CURRENT_INDEX
        self._device_id = config_entry.entry_id
        self._attr_unique_id = self._attr_name + "_index"
        self._attr_native_value = self.coordinator.data["currentCharge"]

    @property
    def icon(self) -> str | None:
        return "mdi:timer-play"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.ENERGY_STORAGE

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def device_info(self) -> DeviceInfo:
        """Donne le lien avec le device. Non utilisé jusqu'au tuto 4"""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=CONF_DEVICE_NAME,
            manufacturer=DEVICE_MANUFACTURER,
            model=DOMAIN,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            self._attr_native_value = self.coordinator.data["currentCharge"]
        except:
            self._attr_native_value = None
        self.async_write_ha_state()


class BatterieVirtuelleTotalInjectionEntity(CoordinatorEntity, SensorEntity):
    """La classe de l'entité TutoHacs"""
    _hass: HomeAssistant
    _username: str
    _password: str

    def __init__(
        self,
        hass: HomeAssistant,  # pylint: disable=unused-argument
        coordinator: USECoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initisalisation de notre entité"""
        super().__init__(coordinator)
        self._hass = hass
        self._attr_has_entity_name = True
        self._attr_name = CONF_BATTERIE_VIRTUELLE_TOTAL_INJECTION
        self._device_id = config_entry.entry_id
        self._attr_unique_id = self._attr_name + "_index"
        self._attr_native_value = self.coordinator.data["totalInjection"]

    @property
    def icon(self) -> str | None:
        return "mdi:timer-play"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.ENERGY_STORAGE

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def device_info(self) -> DeviceInfo:
        """Donne le lien avec le device. Non utilisé jusqu'au tuto 4"""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=CONF_DEVICE_NAME,
            manufacturer=DEVICE_MANUFACTURER,
            model=DOMAIN,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            self._attr_native_value = self.coordinator.data["totalInjection"]
        except:
            self._attr_native_value = None
        self.async_write_ha_state()


class BatterieVirtuelleLastUpdateDateEntity(CoordinatorEntity, SensorEntity):
    """La classe de l'entité TutoHacs"""
    _hass: HomeAssistant

    def __init__(
        self,
        hass: HomeAssistant,  # pylint: disable=unused-argument
        coordinator: USECoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initisalisation de notre entité"""
        super().__init__(coordinator)
        self._hass = hass
        self._attr_has_entity_name = True
        self._attr_name = CONF_BATTERIE_VIRTUELLE_LAST_UPDATE_DATE
        self._device_id = config_entry.entry_id
        self._attr_unique_id = self._attr_name + "_index"
        self._attr_native_value = datetime.fromisoformat(
            self.coordinator.data["updateDate"])

    @property
    def icon(self) -> str | None:
        return "mdi:timer-play"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.DATE

    @property
    def device_info(self) -> DeviceInfo:
        """Donne le lien avec le device. Non utilisé jusqu'au tuto 4"""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=CONF_DEVICE_NAME,
            manufacturer=DEVICE_MANUFACTURER,
            model=DOMAIN,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            self._attr_native_value = datetime.fromisoformat(
                self.coordinator.data["updateDate"])
        except:
            self._attr_native_value = None
        self.async_write_ha_state()
