"""Platform for sensor integration."""
from __future__ import annotations

import logging

from datetime import timedelta
from typing import Any, Dict, Optional

from homeassistant.const import CONF_NAME
from homeassistant.components.sensor import SensorEntity

from .const import (
    CONF_ATTRIB_LIST,
    MODEM_STATE_ATTR
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=15)

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info=None):

    #if discovery_info is None:
    #   return
    
    connection = hass.data[DOMAIN]["connection"]

    status_sensor_name = config.get(CONF_NAME, "zte_status_sensor")
    status_sensor_attributes = config.get(CONF_ATTRIB_LIST, "cell_id,lte_rsrp,signalbar,wan_active_band,spn_name_data")
    status_sensor = StatusSensor(status_sensor_name, status_sensor_attributes, connection)

    add_entities([status_sensor])

class StatusSensor(SensorEntity):
    """
    StatusSensor provides in realtime the values returned by the modem, given a set of user configurable attributes
    which are then passed to the modem API as field selectors.
    
    """
    def __init__(self, name, status_sensor_attributes, connection):
        super().__init__()
        self.attrs: Dict[str, Any] = {}
        self._name = name
        self.sensor_id = "zte_status_sensor"
        self._state = None
        self._available = True
        self.status_sensor_attributes = status_sensor_attributes
        self.connection = connection

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.sensor_id

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    def update(self) -> None:
        """Fetch new state data from the modem API for the sensor.

        """
        try:
            self.connection.manageSession()

            # Always include the modem_main_state attribute in the query as it will be used as the state attribute of the entity:
            status = self.connection.getModemStatus(self.status_sensor_attributes + "," + MODEM_STATE_ATTR)

            # Clear attributes before updating
            self.attrs.clear()

            # Check if status is available
            if status != None:
                modem_attribs = self.status_sensor_attributes.split(",")

                for modem_attrib in modem_attribs:
                    self.attrs[modem_attrib] = status.json()[modem_attrib]

            self._state = status.json()[MODEM_STATE_ATTR]
            self._available = True
        except Exception as ex:
            self._available = False
            _LOGGER.exception("StatusSensor: error retrieving data from ZTE modem: %s", str(ex))
