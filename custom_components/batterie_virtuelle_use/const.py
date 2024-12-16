""" Les constantes pour l'intégration USE """

from homeassistant.const import Platform

DOMAIN = "batterie_virtuelle_use"
PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_BATTERIE_VIRTUELLE_CURRENT_INDEX = "Index batterie virtuelle"
CONF_BATTERIE_VIRTUELLE_TOTAL_INJECTION = "Total injection BV"
CONF_BATTERIE_VIRTUELLE_LAST_UPDATE_DATE = "Date mise à jour index"

CONF_DEVICE_NAME = "Baterie virtuelle USE"

DEVICE_MANUFACTURER = "USE"
