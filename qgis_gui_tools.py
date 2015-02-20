# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Interactive Map Tracking
                                 A QGIS plugin
 Tools for interactive_map_tracking
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

from PyQt4.QtCore import QSettings


def push_state_tool_edit(_s, _name_in_setting, _action):
    """ Push state (activate/desactivate) of QGIS Tool Edit

    :param _s: Qt settings
    :type _s: QSettings

    :param _name_in_setting: name of this param in Qt settings
    :type _name_in_setting: QSting

    :param _action: QGIS Tool edit
    :type _action: QAction

    :return:
    """
    if _action.isChecked():
        _s.setValue("interactive_map_tracking_plugin/" + _name_in_setting, "true")
    else:
        _s.setValue("interactive_map_tracking_plugin/" + _name_in_setting, "false")


def pop_state_tool_edit(_s, _name_in_setting, _action):
    """ Pop state (activate/desactivate) of QGIS Tool Edit

    :param _s: Qt settings
    :type _s: QSettings

    :param _name_in_setting: name of this param in Qt settings
    :type _name_in_setting: QSting

    :param _action: QGIS Tool edit
    :type _action: QAction

    """
    if _s.value("interactive_map_tracking_plugin/" + _name_in_setting, "") == "true":
        _action.activate(0)


def push_state_tools_editing(iface, _s):
    """ Push state (activate/desactivate) of 'all' QGIS Tools edit (Node Tool, Add Feature, Move Feature, Identify)

    :param iface: QGIS Interface
    :type iface: QgsInterface

    :param _s: Qt settings
    :type _s: QSettings

    """
    push_state_tool_edit(_s, "enabledNodeTool", iface.actionNodeTool())
    push_state_tool_edit(_s, "enabledAddFeature", iface.actionAddFeature())
    push_state_tool_edit(_s, "enabledMoveFeature", iface.actionMoveFeature())
    push_state_tool_edit(_s, "enabledIdentify", iface.actionIdentify())


def pop_state_tools_editing(iface, _s):
    """ Pop state (activate/desactivate) of 'all' QGIS Tools edit (Node Tool, Add Feature, Move Feature, Identify)

    :param iface: QGIS Interface
    :type iface: QgsInterface

    :param _s: Qt settings
    :type _s: QSettings

    """
    pop_state_tool_edit(_s, "enabledNodeTool", iface.actionNodeTool())
    pop_state_tool_edit(_s, "enabledAddFeature", iface.actionAddFeature())
    pop_state_tool_edit(_s, "enabledMoveFeature", iface.actionMoveFeature())
    pop_state_tool_edit(_s, "enabledIdentify", iface.actionIdentify())
