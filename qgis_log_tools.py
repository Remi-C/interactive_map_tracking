# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Interactive Map Tracking
                                 A QGIS plugin
 Tools for Interactive_Map_Tracking
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

from qgis.core import QgsMessageLog
import sys

log_tag = "Plugins/Interactive_Map_Tracking"

# TODO : need to clean and use class python (or something better)
# url : http://stackoverflow.com/questions/423379/using-global-variables-in-a-function-other-than-the-one-that-created-them
log_enable = False

def setLogging(bool=True):
    """ Set the logging state (activate/desactivate logging) for IMT

    :param bool: state of IMT logging [default=True]
    :rtype: bool
    """
    global log_enable
    log_enable = bool

def enableLogging():
    """ Activate loggging for IMT """
    global log_enable
    log_enable = True

def disableLogging():
    """ Desactivate loggging for IMT """
    global log_enable
    log_enable = False

def logMessage(message, level=QgsMessageLog.INFO, tag=log_tag, callername=""):
    """ Send a QGIS log message.
    We track the python caller method/class (is useful to know who call the log)

    :param message: Message to log
    :type message: str

    :param level: Level of this log (INFO, WARNING, CRITICAL) [Default=INFO]
    :type level: QgsMessageLog

    :param tag: Tag using for QGIS Log (show in different log tab in QGIS Interface) [default=log_tag="Plugins/Interactive_Map_Tracking"
    :rtype tag: str

    :param callername: String of the caller [default=""]
    :rtype callername: str

    """
    if callername == "":
        callername = sys._getframe().f_back.f_code.co_name
    #
    if log_enable:
        QgsMessageLog.logMessage(callername + " - " + message, tag, level)

def logMessageINFO(message, level=QgsMessageLog.INFO, tag=log_tag):
    """ Send a INFO QGIS log message (Helper using logMessage(...))

    :param message: Message to log
    :type message: str

    :param level: Level of this log (INFO, WARNING, CRITICAL) [Default=INFO]
    :type level: QgsMessageLog

    :param tag: Tag using for QGIS Log (show in different log tab in QGIS Interface) [default=log_tag="Plugins/Interactive_Map_Tracking"
    :rtype tag: str

    """
    logMessage(message, level, tag, sys._getframe().f_back.f_code.co_name)

def logMessageWARNING(message, level=QgsMessageLog.WARNING, tag=log_tag):
    """ Send a WARNING QGIS log message (Helper using logMessage(...))

    :param message: Message to log
    :type message: str

    :param level: Level of this log (INFO, WARNING, CRITICAL) [Default=INFO]
    :type level: QgsMessageLog

    :param tag: Tag using for QGIS Log (show in different log tab in QGIS Interface) [default=log_tag="Plugins/Interactive_Map_Tracking"
    :rtype tag: str

    """
    logMessage(message, level, tag, sys._getframe().f_back.f_code.co_name)

def logMessageCRITICAL(message, level=QgsMessageLog.CRITICAL, tag=log_tag):
    """ Send a CRITICAL QGIS log message (Helper using logMessage(...))

    :param message: Message to log
    :type message: str

    :param level: Level of this log (INFO, WARNING, CRITICAL) [Default=INFO]
    :type level: QgsMessageLog

    :param tag: Tag using for QGIS Log (show in different log tab in QGIS Interface) [default=log_tag="Plugins/Interactive_Map_Tracking"
    :rtype tag: str

    """
    logMessage(message, level, tag, sys._getframe().f_back.f_code.co_name)