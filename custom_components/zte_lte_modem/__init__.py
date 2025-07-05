from __future__ import annotations

import homeassistant.helpers.config_validation as cv

import voluptuous as vol
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.discovery import load_platform
from homeassistant.const import (
    CONF_PROTOCOL,
    CONF_HOST,
    CONF_PASSWORD,
)

from .zte_modem_common import ZteModemConnection

_LOGGER = logging.getLogger(__name__)

DOMAIN = "zte_lte_modem"
PLATFORMS = ["sensor"]

CONFIG_SCHEMA =  vol.Schema(
    {
        DOMAIN: {
            vol.Required(CONF_PROTOCOL): cv.string,
            vol.Required(CONF_HOST): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
        }
    },
    extra=vol.ALLOW_EXTRA,
)

def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    if DOMAIN not in config:
        _LOGGER.debug("setup: domain not in config!")
        return True
    
    protocol = config[DOMAIN].get(CONF_PROTOCOL)
    host =  config[DOMAIN].get(CONF_HOST)
    password = config[DOMAIN].get(CONF_PASSWORD)

    connection = ZteModemConnection(protocol, host, password)

    _LOGGER.debug("setup: created modem connection object.")

    hass.data[DOMAIN] = {"connection": connection}

    load_platform(hass, 'sensor', DOMAIN, {}, hass_config=config)

    return True
