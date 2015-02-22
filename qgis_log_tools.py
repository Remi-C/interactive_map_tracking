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

# ##
### NEW VERSION
###

""" Try to use properly the logging python system

URLs:
- https://docs.python.org/2/library/logging.html
- https://docs.python.org/2/library/logging.handlers.html#logging.StreamHandler
- http://stackoverflow.com/questions/3118059/how-to-write-custom-python-logging-handler
- http://stackoverflow.com/questions/2819791/how-can-i-redirect-the-logger-to-a-wxpython-textctrl-using-a-custom-logging-hand

"""

#url: http://fr.wikipedia.org/wiki/Singleton_(patron_de_conception)#Consid.C3.A9rations_.22avanc.C3.A9es.22
class InheritableSingleton(object):
    # Dictionnaire Python référencant les instances déjà créés
    instances = {}

    def __new__(cls, *args, **kargs):
        if InheritableSingleton.instances.get(cls) is None:
            InheritableSingleton.instances[cls] = object.__new__(cls, *args, **kargs)
        return InheritableSingleton.instances[cls]


import logging
## INIT PYTHON LOGGING
#url: http://stackoverflow.com/questions/12034393/import-side-effects-on-logging-how-to-reset-the-logging-module
logging.shutdown()
reload(logging)


class QGISLogHandler(logging.Handler):
    """

        """

    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        try:
            msg = self.format(record)
            QgsMessageLog.logMessage(msg)
        except:
            self.handleError(record)


class QGISLoggerGeneric():
    """

    """

    def __init__(self):
        ## INIT PYTHON LOGGER ###
        #url: http://stackoverflow.com/questions/12034393/import-side-effects-on-logging-how-to-reset-the-logging-module
        root = logging.getLogger()
        map(root.removeHandler, root.handlers[:])
        map(root.removeFilter, root.filters[:])

        #logging.basicConfig(format="[%(asctime)s %(threadName)s, %(levelname)s] %(message)s")
        #
        # see def basicConfig(**kwargs) in __init__.py for logging python module
        # fs =  format    Use the specified format string for the handler.
        # dfs=  datefmt   Use the specified date/time format.
        #
        fs = "[%(asctime)s %(threadName)s, %(levelname)s] %(message)s"
        dfs = None
        # see class Formatter(object) in __init__.py for logging python module
        # Formatter instances are used to convert a LogRecord to text.
        qgis_formatter = logging.Formatter(fs, dfs)

        qgis_handler = QGISLogHandler()
        qgis_handler.setFormatter(qgis_formatter)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(qgis_handler)

    def log(self, msg):
        self.logger.info(msg)


# Specialisation
class QGISLoggerSingleton(QGISLoggerGeneric, InheritableSingleton):
    pass

# alias class name
QGISLogger = QGISLoggerSingleton
