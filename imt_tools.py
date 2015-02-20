# -*- coding: utf-8 -*-
"""
/***************************************************************************
 interactive map tracking
                                 A QGIS plugin
 Tools for Interactive Map Tools
                              -------------------
        begin                : 2015-02-10
        git sha              : $Format:%H$
        copyright            : (C) 2015 by IGN
        email                : lionel.atty@ign.fr
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'latty'

from qgis.core import *

import os
import socket


#
if os.name != "nt":
    import fcntl
    import struct
    def get_interface_ip(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24])


def get_lan_ip():
    """ Finding the ip lan address (OS independant)
     url: http://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib#

    :return: String of the IP
    :rtype: str
    """
    ip = socket.gethostbyname(socket.gethostname())
    if ip.startswith("127.") and os.name != "nt":
        interfaces = ["eth0","eth1","eth2","wlan0","wlan1","wifi0","ath0","ath1","ppp0"]
        for ifname in interfaces:
            try:
                ip = get_interface_ip(ifname)
                break;
            except IOError:
                pass
    return ip


def find_index_field_by_name(field_names, field_name):
    """ Search a field (by name) in a list of fields.

    :param field_names: list of field name
    :type field_names: list[str]

    :param field_name: field name
    :type field_name: str

    :return: If found return the index of the field in the list Else return -1
    :rtype: int
    """
    # find index for field 'user-id'
    try:
        id_for_user_id = field_names.index(field_name)
    except ValueError:
        # field non trouve !
        return -1
    return id_for_user_id


# url: http://stackoverflow.com/questions/117014/how-to-retrieve-name-of-current-windows-user-ad-or-local-using-python
def get_os_username():
    """

    :return:
    """
    import getpass
    return getpass.getuser()


def get_timestamp_from_qt_string_format(QtDateFormat=1):
    """ Retrieve timestamp from the system and convert into a ISO QString/QDateTime format.

    urls:
    - https://docs.python.org/2/library/datetime.html
    - http://stackoverflow.com/questions/2935041/how-to-convert-from-timestamp-to-date-in-qt
    - http://stackoverflow.com/questions/3387655/safest-way-to-convert-float-to-integer-in-python
    - http://pyqt.sourceforge.net/Docs/PyQt4/qt.html -> Qt.DateFormat
      Qt.ISODate 	= 1 : ISO 8601 extended format: either YYYY-MM-DD for dates or YYYY-MM-DDTHH:mm:ss, YYYY-MM-DDTHH:mm:ssTZD
      (e.g., 1997-07-16T19:20:30+01:00) for combined dates and times.

    :param QtDateFormat: enum (value) for ISO conversion (from Qt C++ API) [default=1(=Qt.ISODate)]
    :type QtDateFormat: int

    :return: TimeStamp in ISO QString from QDateTime format.
    :rtype: QString
    """
    import time
    from PyQt4.QtCore import QDateTime
    # Python time
    timestamp = time.time()
    # Qt time
    qdatetime = QDateTime()
    qdatetime.setTime_t(int(timestamp))
    # String Qt time
    return qdatetime.toString(1)

def construct_listpoints_from_extent(_extent):
    """ Construct a list of QGIS points from QGIS extent.

    :param _extent: QGIS extent
    :type _extent: QgsRectangle

    :return: List of QGIS points
    :rtype: list[QgsPoint]
    """
    x1 = _extent.xMinimum()
    y1 = _extent.yMinimum()
    x3 = _extent.xMaximum()
    y3 = _extent.yMaximum()
    x2 = x1
    y2 = y3
    x4 = x3
    y4 = y1
    return [QgsPoint(x1, y1),
            QgsPoint(x2, y2),
            QgsPoint(x3, y3),
            QgsPoint(x4, y4),
            QgsPoint(x1, y1)]

