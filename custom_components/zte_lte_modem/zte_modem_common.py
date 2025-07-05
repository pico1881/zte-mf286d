import hashlib
import requests
import re
import logging
import sys
import urllib.parse
import datetime
import dateutil.tz
import smsutil

from jsonpath_ng.ext import parse

ZTE_API_BASE = '/goform/'

GET_CMD = 'goform_get_cmd_process'
SET_CMD = 'goform_set_cmd_process'

# TODO comment this when using in the integration:
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

_LOGGER = logging.getLogger(__name__)


"""
ZTE modem connection management class
"""

class ZteModemConnection:
    def __init__(self, protocol, host, password):
        self.protocol = protocol
        self.host = host
        self.password = password
        self.url = protocol + '://' + host
        self.cookie = ''

    def getDeviceVersion(self):
        
        headers = { "Referer": self.url + "/index.html", "Host": self.host, "Accept": "application/json, text/javascript, */*; q=0.01" }
        params = {"isTest": "false", "cmd": "Language%2Ccr_version%2Cwa_inner_version", "multi_data": "1" }

        return requests.get(self.url + ZTE_API_BASE + GET_CMD, params=params, headers=headers)

    def sendLoginCommand(self, crVersion, waInnerVersion, ld, rd):
        headers = { "Origin": self.url, "Referer": self.url + "/index.html", "Host": self.host, "Accept": "application/json, text/javascript, */*; q=0.01" }
        passwordHash = calculatePasswordHash(self.password)

        params = { "isTest": "false", "goformId": "LOGIN", "password": passwordHash}

        return requests.post(self.url + ZTE_API_BASE + SET_CMD, data=params, headers=headers)

    def getModemStatus(self, attributeList):
        headers = { "Referer": self.url + "/index.html", "Host": self.host, "Accept": "application/json, text/javascript, */*; q=0.01", "Cookie": self.cookie }
        #params = { "multi_data": "1", "isTest": "false", "sms_received_flag_flag": "0", "sts_received_flag_flag": "0", "cmd": "modem_main_state,pin_status,opms_wan_mode,opms_wan_auto_mode,loginfo,new_version_state,current_upgrade_state,is_mandatory,wifi_dfs_status,battery_value,ppp_dial_conn_fail_counter,signalbar,network_type,network_provider,opms_wan_auto_mode,dhcp_wan_status,ppp_status,EX_SSID1,sta_ip_status,EX_wifi_profile%,m_ssid_enable,RadioOff,wifi_onoff_state,wifi_chip1_ssid1_ssid,wifi_chip2_ssid1_ssid,simcard_roam,lan_ipaddr,station_mac,wifi_access_sta_num,battery_charging,battery_vol_percent,battery_pers,spn_name_data,spn_b1_flag,spn_b2_flag,realtime_tx_bytes,realtime_rx_bytes,realtime_time,realtime_tx_thrpt,realtime_rx_thrpt,monthly_rx_bytes,monthly_tx_bytes,monthly_time,date_month,data_volume_limit_switch,data_volume_limit_size,data_volume_alert_percent,data_volume_limit_unit,roam_setting_option,upg_roam_switch,cbns_server_enable,app_debug_mode,odu_mode,ssid,wifi_enable,wifi_5g_enable,check_web_conflict,dial_mode,ppp_dial_conn_fail_counter,wan_lte_ca,privacy_read_flag,is_night_mode,pppoe_status,dhcp_wan_status,static_wan_status,vpn_conn_status,rmcc,rmnc,sms_received_flag,sts_received_flag,sms_unread_num" }
        params = { "multi_data": "1", "isTest": "false", "cmd": attributeList }

        return requests.get(self.url + ZTE_API_BASE + GET_CMD, params=params, headers=headers)

    def getLteStatus(self):
        headers = { "Referer": self.url + "/index.html", "Host": self.host, "Accept": "application/json, text/javascript, */*; q=0.01", "Cookie": self.cookie }
        params = { "isTest": "false", "cmd": "network_type,rssi,rscp,lte_rsrp,Z5g_snr,Z5g_rsrp,ZCELLINFO_band,Z5g_dlEarfcn,lte_ca_pcell_arfcn,lte_ca_pcell_band,lte_ca_scell_band,lte_ca_pcell_bandwidth,lte_ca_scell_info,lte_ca_scell_bandwidth,wan_lte_ca,lte_pci,Z5g_CELL_ID,Z5g_SINR,cell_id,wan_lte_ca,lte_ca_pcell_band,lte_ca_pcell_bandwidth,lte_ca_scell_band,lte_ca_scell_bandwidth,lte_ca_pcell_arfcn,lte_ca_scell_arfcn,lte_multi_ca_scell_info,wan_active_band,nr5g_pci,nr5g_action_band,nr5g_cell_id", "multi_data": "1"}

        return requests.get(self.url + ZTE_API_BASE + GET_CMD, params=params, headers=headers)


    def login(self):
        resp = self.getDeviceVersion()

        _LOGGER.debug('login: getDeviceVersion response: %s', str(resp.content))

        query = parse('$.cr_version')
        crVersion = query.find(resp.json())[0].value

        _LOGGER.debug('login: crVersion = %s', str(crVersion))

        query = parse('$.wa_inner_version')
        waInnerVersion = query.find(resp.json())[0].value

        _LOGGER.debug('login: waInnerVersion = %s', str(waInnerVersion))

        resp = self.getLd()

        query = parse('$.LD')
        ld = query.find(resp.json())[0].value
        
        _LOGGER.debug('login: ld = %s', str(ld))

        resp = self.getRd()
        query = parse('$.RD')
        rd = query.find(resp.json())[0].value

        _LOGGER.debug('login: rd = %s', str(rd))

        resp =  self.sendLoginCommand()

        if ( result := resp.json()['result'] ) != '0':
            raise ZteModemException("Non-successful login result: ", result)
        
        _LOGGER.debug('login: http response: %s, body: %s', str(resp.status_code), str(resp.content))

        cookieHeader = resp.headers.get("Set-Cookie")

        pattern = re.compile('stok\=\".*\"')

        _LOGGER.debug('login: cookieHeader: %s', str(cookieHeader))

        result = pattern.search(cookieHeader)
        
        self.cookie = result.group(0)
        _LOGGER.debug('login: cookie: %s', str(self.cookie))


    def logout(self):
        """
        logout closes the session with the modem, invalidating the session cookie.

        :return: a json payload containing "result": "success" in case of a successful logout.
        """
        headers = { "Origin": self.url, "Referer": self.url + "/index.html", "Host": self.host, "Accept": "application/json, text/javascript, */*; q=0.01" }
        params = { "isTest": "false", "goformId": "LOGOUT", "AD": self.ad}

        return requests.post(self.url + ZTE_API_BASE + SET_CMD, data=params, headers=headers)

    def checkLoginStatus(self):
        headers = { "Referer": self.url + "/index.html", "Host": self.host, "Accept": "application/json, text/javascript, */*; q=0.01", "Cookie": self.cookie }
        params = { "multi_data": "1", "isTest": "false", "cmd": "loginfo" }

        return requests.get(self.url + ZTE_API_BASE + GET_CMD, params=params, headers=headers)

    def manageSession(self):
        loginStatus = self.checkLoginStatus()

        # If there isn't a valid session, try to login:
        if loginStatus.json()['loginfo'] == '':
            self.login()
            loginStatus = self.checkLoginStatus()

        if loginStatus.json()['loginfo'] != 'ok':
            raise ZteModemException("Unsucessful login or modem busy with another user.")

# Exceptions

class ZteModemException(Exception):
    """Raise for my specific kind of exception"""

# Utility operations:

def calculatePasswordHash(password):
    prefixHash =  hashlib.sha256(password.encode('utf-8')).hexdigest().upper()

    return prefixHash

