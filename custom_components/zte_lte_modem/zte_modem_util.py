from zte_modem_common import ZteModemConnection

import smsutil
import json
import datetime

from getpass import getpass

"""
Utility module for testing the zte_modem_common library functions.
"""

def doGetModemStatus(connection, attributeList):
    connection.login()
    resp = connection.getModemStatus(attributeList)
    print('zte_modem_util: doGetModemStatus: ', json.dumps(resp.json(), indent=4))

def doGetLteStatus(connection):
    connection.login()
    resp = connection.getLteStatus()
    print('zte_modem_util: doGetLteStatus: ', json.dumps(resp.json(), indent=4))


def doCheckUser(connection):
    resp = connection.checkLoginStatus()
    print('zte_modem_util: doCheckUser: ', json.dumps(resp.json(), indent=4))


connection = ZteModemConnection('http', 'localhost', getpass())

connection.login()
