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

from PyQt4.QtCore import QSettings
from PyQt4.QtGui import QAbstractButton, QCheckBox


try:
    import cPickle as pickle
except:
    import pickle
import qgis_log_tools
from collections import namedtuple

defaultQtDateFormatString = "yyyy-MM-ddThh:mm:ss.zzz"

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
        interfaces = ["eth0", "eth1", "eth2", "wlan0", "wlan1", "wifi0", "ath0", "ath1", "ppp0"]
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


def get_timestamp():
    import time
    # Python time
    return time.time()


def convert_timestamp_to_qdatetime(timestamp):
    from PyQt4.QtCore import QDateTime
    from math import modf

    timestamp_frac, timestamp_whole = modf(timestamp)
    # Qt time
    qdatetime = QDateTime()
    qdatetime.setTime_t(int(timestamp_whole))
    qdatetime = qdatetime.addMSecs(int(timestamp_frac * 1000))
    #
    return qdatetime


# def convert_timestamp_to_qt_string_format(timestamp, QtDateFormat):
# # String Qt time
# return convert_timestamp_to_qdatetime(timestamp).toString(QtDateFormat)


def convert_timestamp_to_qt_string_format(timestamp, QtDateFormatString=defaultQtDateFormatString):
    # String Qt time
    return convert_timestamp_to_qdatetime(timestamp).toString(QtDateFormatString)


# def get_timestamp_from_qt_string_format(QtDateFormat):
#     """ Retrieve timestamp from the system and convert into a ISO QString/QDateTime format.
#
#     urls:
#     - https://docs.python.org/2/library/datetime.html
#     - http://stackoverflow.com/questions/2935041/how-to-convert-from-timestamp-to-date-in-qt
#     - http://stackoverflow.com/questions/3387655/safest-way-to-convert-float-to-integer-in-python
#     - http://pyqt.sourceforge.net/Docs/PyQt4/qt.html -> Qt.DateFormat
#       Qt.ISODate 	= 1 : ISO 8601 extended format: either YYYY-MM-DD for dates or YYYY-MM-DDTHH:mm:ss, YYYY-MM-DDTHH:mm:ssTZD
#       (e.g., 1997-07-16T19:20:30+01:00) for combined dates and times.
#
#     :param QtDateFormat: enum (value) for ISO conversion (from Qt C++ API) [default=1(=Qt.ISODate)]
#     :type QtDateFormat: int
#
#     :return: TimeStamp in ISO QString from QDateTime format.
#     :rtype: QString
#     """
#     return convert_timestamp_to_qt_string_format(get_timestamp(), QtDateFormat)


def get_timestamp_from_qt_string_format(QtDateFormatString=defaultQtDateFormatString):
    return convert_timestamp_to_qt_string_format(get_timestamp(), QtDateFormatString)


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


def find_layer_in_qgis_legend_interface(_iface, _layername):
    """

    :param _iface:
    :param _layername:
    :return:
    """
    try:
        layer_searched = [layer_searched
                          for layer_searched in _iface.legendInterface().layers()
                          if layer_searched.name() == _layername]
        return layer_searched[0]
    except:
        return None


import time


class TpTimer:
    def __init__(self):
        self.currentTime = self.default_timers()
        self.dict_process_timeupdate = {}
        self.dict_process_delay = {}

    @staticmethod
    def default_timers():
        return [time.time(), time.time()]

    @staticmethod
    def default_delay():
        return 0.0

    def get_current_time(self):
        self.update_current_time()
        return self.currentTime[0]

    def __getitem__(self, key):
        return self.dict_process_timeupdate.setdefault(key, self.default_timers())

    def update_current_time(self):
        self.currentTime = [time.time(), self.currentTime[0]]

    def delta(self):
        return self.currentTime[0] - self.currentTime[1]

    def delta(self, key):
        list_times = self.__getitem__(key)
        return list_times[0] - list_times[1]

    def delta_with_current_time(self, key):
        self.update_current_time()
        list_times = self.__getitem__(key)
        return self.currentTime[0] - list_times[0]

    def update(self, key):
        self.update_current_time()
        list_times = self.__getitem__(key)
        self.dict_process_timeupdate[key] = [self.currentTime[0], list_times[0]]
        return self.dict_process_timeupdate[key]

    def get_delay(self, process_name):
        return self.dict_process_delay.setdefault(process_name, self.default_delay())

    def set_delay(self, delay_name, time_delay):
        self.dict_process_delay[delay_name] = time_delay

    def is_time_to_update(self, process_name, delay_name):
        return self.delta_with_current_time(process_name) >= self.get_delay(delay_name)


import shlex
from subprocess import call, PIPE, STDOUT


def get_return_code_of_simple_cmd(cmd, stderr=STDOUT):
    """Execute a simple external command and return its exit status."""
    args = shlex.split(cmd)
    return call(args, stdout=PIPE, stderr=stderr)


def is_network_alive(url="www.google.com"):
    #cmd = "ping -c 1 " + url
    cmd = "curl --output /dev/null --silent --head --fail" + url
    return get_return_code_of_simple_cmd(cmd) == 0


from PyQt4.QtNetwork import QTcpSocket


def isConnected(url):
    socket = QTcpSocket()
    socket.connectToHost(url, 80)
    return socket.waitForConnected(1000)


DEFAULT_SEGMENT_EPSILON = 1e-08


def extent_equal(r1, r2, epsilon=DEFAULT_SEGMENT_EPSILON):
    return abs(r1.xMaximum() - r2.xMaximum()) <= epsilon and \
           abs(r1.yMaximum() - r2.yMaximum()) <= epsilon and \
           abs(r1.xMinimum() - r2.xMinimum()) <= epsilon and \
           abs(r1.yMinimum() - r2.yMinimum()) <= epsilon


qsettings_id_pickle = "pickle"
#
pickle_id_gui = "GUI"
pickle_id_list_checkbox = "list_checkbox"
pickle_id_list_tabs_size = "list_tabs_size"


def save_gui_states_in_qsettings(dict_qobject_slot):
    """

    :param dict_qobject_slot:
    """
    s = QSettings()
    #
    for qobject in dict_qobject_slot.keys():
        slot = dict_qobject_slot[qobject]
        id_string = slot.__name__
        s.setValue(id_string, str(qobject.isChecked()))


def serialize_checkbox(checkbox):
    """

    :param checkbox:
    :return:
    """
    return {
        'isEnabled': checkbox.isEnabled(),
        'isChecked': checkbox.isChecked()
    }


def serialize_list_checkbox(dlg, list_id_checkbox):
    """

    :return:
    """
    return_dict = {}
    for string_id_checkbox in list_id_checkbox:
        qt_checkbox = dlg.__getattribute__(string_id_checkbox)
        dict_checkbox_id = {
            string_id_checkbox: serialize_checkbox(qt_checkbox)
        }
        return_dict.update(dict_checkbox_id)
    return return_dict


def serialize_tabs_size(imt):
    """

    :param dlg:
    :return:
    """
    return imt.dict_tabs_size


def update_checkbox_from_serialization(qobject, id_qobject, state):
    """

    :param state:
    :param qobject:
    :param id_qobject:
    :return:
    """
    qobject.setEnabled(state[pickle_id_gui][pickle_id_list_checkbox][id_qobject].setdefault('isEnabled', True))
    qobject.setChecked(state[pickle_id_gui][pickle_id_list_checkbox][id_qobject].setdefault('isChecked', False))
    #
    # print state[pickle_id_gui][pickle_id_list_checkbox][id_qobject], ' * ', \
    # id_qobject, ' * ', \
    #     state[pickle_id_gui][pickle_id_list_checkbox][id_qobject].setdefault('isChecked', False)


def update_list_checkbox_from_serialization(dlg, list_string_id_checkbox, pickle_state):
    """

    :param dlg:
    :param list_string_id_checkbox:
    :param pickle_state:
    :return:
    """
    for string_id_dlg in list_string_id_checkbox:
        qt_checkbox = dlg.__getattribute__(string_id_dlg)
        update_checkbox_from_serialization(qt_checkbox, string_id_dlg, pickle_state)


def update_tabs_size_from_serialization(imt, pickle_state):
    """

    :param imt:
    :param pickle_state:
    :return:
    """
    imt.dict_tabs_size = pickle_state[pickle_id_gui][pickle_id_list_tabs_size]


def saves_states_in_qsettings_pickle(imt, pickle_name_in_qsettings=qsettings_id_pickle):
    """

    :param imt:
    """
    pickle_string_dump = ""
    try:
        pickle_string_dump = pickle.dumps(imt)
    finally:
        imt.qsettings.beginGroup(imt.qsettings_group_name)
        imt.qsettings.setValue(pickle_name_in_qsettings, pickle_string_dump)
        imt.qsettings.endGroup()


def restore_states_from_pickle(imt, pickle_name_in_qsettings=qsettings_id_pickle):
    """

    :return:
    """

    qsettings = imt.qsettings
    qsettings.beginGroup(imt.qsettings_group_name)
    qsettings_pickle = qsettings.value(pickle_name_in_qsettings)
    qsettings.endGroup()

    # print "in QSettings - pickle: ", qsettings_pickle
    if qsettings_pickle:
        imt_for_states = None
        try:
            imt_for_states = pickle.loads(str(qsettings_pickle))
        finally:
            state = imt_for_states.getState()
            imt.restoreState(state)
    # else:
    # update_list_checkbox_from_qsettings(imt)

    #TODO: test on QT dump
    test_qt_dump(imt)


# url: http://stackoverflow.com/questions/121396/accessing-object-memory-address
# url: https://docs.python.org/2/reference/datamodel.html#object.__repr__
# url: http://stackoverflow.com/questions/1810526/python-calling-a-method-of-an-instances-member-by-name-using-getattribute
# url: https://docs.python.org/2/library/functions.html#id

def build_list_id_filter_by_qt_type(dlg, qt_type):
    """

    :param dlg:
    :param qt_type:
    :return:
    """
    list_id = []
    list_children = dlg.findChildren(qt_type)
    for qt_object in list_children:
        qt_object_id = id(qt_object)
        list_id.append(qt_object_id)
    return list_id


def build_dict_id_qt_type(dlg, qt_type):
    """

    :param dlg:
    :param qt_type:
    :return:
    """
    dict_id_qt_type = {}
    list_id_for_qt_type = build_list_id_filter_by_qt_type(dlg, qt_type)
    for qt_object_id in list_id_for_qt_type:
        dict_id_qt_type[qt_object_id] = qt_type
    return dict_id_qt_type


def build_list_member_name_filter_by_qtype(dlg, *qt_types):
    """

    :param dlg:
    :return:
    """
    list_member_name = []
    for qt_type in qt_types:
        dict_id_qt_type = build_dict_id_qt_type(dlg, qt_type)
        dlg_dict = dlg.__getattribute__('__dict__')
        for dlg_id_string_member in dlg_dict:
            # get the Qt object member associated
            qt_object = dlg_dict[dlg_id_string_member]
            # get the 'unique' python id
            unique_id_qt_object = id(qt_object)
            if unique_id_qt_object in dict_id_qt_type:
                list_member_name.append(dlg_id_string_member)
    return list_member_name


def build_list_member_name_filter_by_qtypes(dlg, *qt_types):
    """

    :param dlg:
    :param qt_types:
    :return:
    """
    return_list = []
    for qt_type in qt_types:
        return_list.extend(build_list_member_name_filter_by_qtype(dlg, qt_type))
    return return_list


def build_list_member_name_filter_qcheckbox(dlg):
    """

    :param dlg:
    :return:
    """
    return build_list_member_name_filter_by_qtypes(dlg, QCheckBox)


def test_qt_dump(imt):
    """
    Show a connection between Python class and Qt Gui (wrapper)
    :param imt:
    """
    list_qt_types = [
        QAbstractButton
    ]
    dict_id_qt_type = {}
    for qt_type in list_qt_types:
        dict_id_qt_type.update(build_dict_id_qt_type(imt.dlg, qt_type))

    # list_id_for_qabstractbutton = []
    # list_children = imt.dlg.findChildren(QAbstractButton)
    # for qt_button in list_children:
    # qgis_log_tools.logMessageINFO("* From Qt, filter 'QAbstractButton'" + "\n" +
    #                                   "\t- text: " + qt_button.text() + "\n" +
    #                                   "\t- isChecked: " + str(qt_button.isChecked()) + "\n" +

    #                                   "\t- python mem: " + str(qt_button.__repr__) + "\n")
    #     # url: https://docs.python.org/2/library/functions.html#id
    #     list_id_for_qabstractbutton.append(id(qt_button))

    # url: http://stackoverflow.com/questions/1810526/python-calling-a-method-of-an-instances-member-by-name-using-getattribute
    # get member from interactive_map_tracking dlg (Qt Gui)
    imt_dlg_dict = imt.dlg.__getattribute__('__dict__')
    for imt_dlg_id_string_member in imt_dlg_dict.keys():
        # url: http://stackoverflow.com/questions/16408472/print-memory-address-of-python-variable
        # get the Qt object member associated
        qt_object = imt_dlg_dict[imt_dlg_id_string_member]
        # get the 'unique' python id
        unique_id_qt_object = id(qt_object)
        if unique_id_qt_object in dict_id_qt_type:
            qgis_log_tools.logMessageINFO("* From IMT Python class, find Qt element (in dlg)" + "\n" +
                                          "\t- Member name: " + imt_dlg_id_string_member + "\n" +
                                          "\t- Qt type: " + str(dict_id_qt_type[unique_id_qt_object]) + "\n" +
                                          "\t-- isChecked: " + str(qt_object.isChecked()))


def update_list_checkbox_from_qsettings(imt):
    """
    CONDITION: init_signals need to be call before init_plugin
    otherwise signals_manager have no information about signals
    and we can't rely slot signature with qobject
    :return:
    """
    s = imt.qsettings
    s.beginGroup(imt.qsettings_group_name)
    restore_gui_states_from_qsettings(imt)
    s.endGroup()


def restore_gui_states_from_qsettings(imt, b_launch_slot=True):
    """

    :param list_dlg_id_slot:
    """
    s = imt.qsettings
    for tuple_dlg_id_slot in imt.list_tuples_dlg_id_slot:
        # print qobject, type(qobject )
        qobject = tuple_dlg_id_slot[0]
        id_slot = tuple_dlg_id_slot[2]
        id_in_qsetting = id_slot
        qobject_is_checked = eval(s.value(id_in_qsetting, "False"))
        qobject.setChecked(qobject_is_checked)
        #
        if b_launch_slot:
            slot = imt.signals_manager.get_slot(qobject, id_slot)
            if slot:
                slot()
                #
                # print "id_in_qsetting: ", id_in_qsetting, " - value: ", s.value(id_in_qsetting, "False")


def print_group_name_values_in_qsettings(group_name=""):
    """

    :param group_name:
    :return:
    """
    qsettings = QSettings()
    keys = [x for x in qsettings.allKeys() if group_name in x]
    for key in keys:
        print key, str(qsettings.value(key))
        # import qgis_log_tools
        # qgis_log_tools.logMessageINFO(str(key)+": "+str(qsettings.value(key)))


def get_itemData(combobox):
    """

    :param combobox:
    :return:
    """
    return combobox.itemData(combobox.currentIndex())


def get_itemText(combobox):
    """

    :param combobox:
    :return:
    """
    return combobox.itemText(combobox.currentIndex())


def create_named_tuple_from_names(name, list_names):
    """

    :param list_names:
    :return:
    """
    return namedtuple(name, list_names)


# url: http://stackoverflow.com/questions/16377215/how-to-pickle-a-namedtuple-instance-correctly
# url: https://docs.python.org/2/library/functions.html#globals
def CreateNamedOnGlobals(*args):
    import collections
    namedtupleClass = collections.namedtuple(*args)
    globals()[namedtupleClass.__name__] = namedtupleClass
    return namedtupleClass