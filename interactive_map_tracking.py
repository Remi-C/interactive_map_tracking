# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
/***************************************************************************
 interactive_map_tracking
                                 A QGIS plugin
 A QGIS 2.6 plugin to track camera of user , AND/OR to autocommit/refresh edit on PostGIS vector layer
                              -------------------
        begin                : 2015-02-20
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Lionel Atty, IGN, SIDT
        email                : remi.cura@gmail.com
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from interactive_map_tracking_dialog import interactive_map_trackingDialog
import os.path

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtCore import QObject, SIGNAL, QUrl
# from PyQt4.QtCore import QMutex, QWaitCondition
from PyQt4.QtGui import QAction, QIcon, QTabWidget
from PyQt4.QtWebKit import QWebSettings, QWebView

from qgis.gui import QgsMessageBar

from qgis.core import *

import qgis_layer_tools
import qgis_mapcanvas_tools
import qgis_log_tools
import imt_tools

#
# for beta test purposes
#
from PyQt4.QtCore import QTimer
import Queue

from collections import namedtuple

import time

import threading


def CONVERT_S_TO_MS(s):
    return s*1000

# with Qt resources files
# gui_doc_about = ":/plugins/interactive_map_tracking/gui_doc/About.htm"
# gui_doc_user_doc = ":/plugins/interactive_map_tracking/gui_doc/Simplified_User_Guide.htm"

# with absolute (os) path
qgis_plugins_directory = QgsApplication.qgisSettingsDirPath()[:-1] + "python/plugins/" + "interactive_map_tracking/"
webview_offline_about = qgis_plugins_directory + "gui_doc/" + "About.htm"
webview_offline_user_doc = qgis_plugins_directory + "gui_doc/" + "Simplified_User_Guide.htm"
webview_online_about = "https://github.com/Remi-C/interactive_map_tracking/wiki/[User]-About"
webview_online_user_doc = "https://github.com/Remi-C/interactive_map_tracking/wiki/[User]-User-Guide"

class interactive_map_tracking:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """

        import time

        current_time = time.time()

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'interactive_map_tracking_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = interactive_map_trackingDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Interactive Map Tracking')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'interactive_map_tracking')
        self.toolbar.setObjectName(u'interactive_map_tracking')

        # self.selections = []
        self.qsettings_prefix_name = "imt/"

        self.bSignalForLayerModifiedConnected = False
        self.bSignalForLayerChangedConnected = False
        self.bSignalForExtentsChangedConnected = False

        # self.idCameraPositionLayerInBox = 0
        self.currentLayerForTrackingPosition = None

        self.bSignalForProjectReadConnected = True
        QObject.connect(self.iface, SIGNAL("projectRead()"), self.qgisInterfaceProjectRead)

        # MUTEX
        self.bUseV2Functionnalities = self.dlg.enableUseMutexForTP.isChecked()

        # url: https://docs.python.org/2/library/collections.html#collections.namedtuple
        # Definition : namedtuples 'type'
        self.TP_NAMEDTUPLE_LET = namedtuple('TP_NAMEDTUPLE_LET', ['layer', 'extent', 'w_time'])
        self.TP_NAMEDTUPLE_ET = namedtuple('TP_NAMEDTUPLE_ET', ['extent', 'w_time'])
        # LIFO Queue to save (in real time) requests for tracking position
        self.tp_queue_rt_ntuples_let = Queue.LifoQueue()
        # self.tp_rt_ntuples_let = self.TP_NAMEDTUPLE_LET(None, None, current_time)
        self.tp_dict_key_l_values_et = {}
        self.tp_list_fets = []
        self.tp_dict_key_l_values_listfeatures = {}
        self.tp_dict_layers_to_commit = {}
        #
        self.qtimer_tracking_position_rtt_to_memory = QTimer()
        self.qtimer_tracking_position_rtt_to_memory.timeout.connect(self.tracking_position_qtimer_rttp_to_memory)
        self.qtimer_tracking_position_memory_to_geom = QTimer()
        self.qtimer_tracking_position_memory_to_geom.timeout.connect(self.tracking_position_qtimer_memory_to_geom)
        self.qtimer_tracking_position_geom_to_layer = QTimer()
        self.qtimer_tracking_position_geom_to_layer.timeout.connect(self.tracking_position_qtimer_geom_to_layer)
        self.qtimer_tracking_position_layers_to_commit = QTimer()
        self.qtimer_tracking_position_layers_to_commit.timeout.connect(self.tracking_position_qtimer_layers_to_commit)

        # OPTIONS: timing reactions
        #
        self.tp_timers = imt_tools.TpTimer()
        # TODO : add this options timing on GUI
        # in S
        tp_threshold_time_for_realtime_tracking_position = 0.125  # i.e. 8hz => (max) 8 tracking positions record per second
        # in MS
        tp_threshold_time_for_tp_to_mem = 250  # add to reference timing: realtime_tracking_position
        tp_threshold_time_for_construct_geom = 50  # add to reference timing: tp_to_mem
        tp_threshold_time_for_sending_geom_to_layer = 100  # add to reference timing: construct_geom
        tp_threshold_time_for_sending_layer_to_dp = 100  # add to reference timing: sending_geom_to_layer
        #
        self.tp_timers.set_delay("tp_threshold_time_for_realtime_tracking_position",
                                 tp_threshold_time_for_realtime_tracking_position)
        self.tp_timers.set_delay("tp_threshold_time_for_tp_to_mem", tp_threshold_time_for_tp_to_mem)
        self.tp_timers.set_delay("tp_threshold_time_for_construct_geom", tp_threshold_time_for_construct_geom)
        self.tp_timers.set_delay("tp_threshold_time_for_sending_geom_to_layer",
                                 tp_threshold_time_for_sending_geom_to_layer)
        self.tp_timers.set_delay("tp_threshold_time_for_sending_layer_to_dp", tp_threshold_time_for_sending_layer_to_dp)
        # in S
        delay_time_still_moving = 0.750  # delta time used to decide if the user still moving on the map
        self.tp_timers.set_delay("delay_time_still_moving", delay_time_still_moving)
        # for timing
        self.tp_time_last_rttp_to_mem = current_time
        self.tp_time_last_construct_geom = current_time
        self.tp_time_last_send_geom_to_layer = current_time
        self.tp_time_last_send_layer_to_dp = current_time

        self.tp_queue_qgis_event_to_mem = []

        """
        Delay on manager of trackposition requests
        can be interesting to evaluate/benchmark the impact on this value
        """
        self.qtimer_tracking_position_delay = self.tp_timers.get_delay(
            "p_threshold_time_for_realtime_tracking_position")  # in ms

        # user-id:
        # from user id OS
        os_username = imt_tools.get_os_username()
        # try to use IP to identify the user
        user_ip = imt_tools.get_lan_ip()
        #
        self.tp_user_name = os_username + " (" + user_ip + ")"

        # default value for threshold scale
        self.threshold = 300

        self.tp_id_user_id = 0
        self.tp_id_w_time = 0
        self.values = []

        self.bRefreshMapFromAutoSave = False

        self.TP_NAMEDTUPLE_WEBVIEW = namedtuple('TP_NAMEDTUPLE_WEBVIEW', ['state', 'width', 'height', 'online_url', 'offline_url'])
        self.webview_dict = {}
        self.webview_default_tuple = self.TP_NAMEDTUPLE_WEBVIEW(0, 0, 0, None, None)
        self.webview_dict[self.dlg.webView_userdoc] = self.TP_NAMEDTUPLE_WEBVIEW(0, 0, 0, webview_online_user_doc, webview_offline_user_doc)
        self.webview_dict[self.dlg.webView_about] = self.TP_NAMEDTUPLE_WEBVIEW(0, 0, 0, webview_online_about, webview_offline_about)
        self.current_webview = None
        self.webview_margin = 60

        self.dict_tabs_size = {}

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('interactive_map_tracking', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        qgis_log_tools.logMessageINFO("Launch 'InitGui(...)' ...")

        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/interactive_map_tracking/icon.png'
        # icon_path = ':/plugins/interactive_map_tracking/icon_svg.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Tools for Interactive Map Tracking'),
            callback=self.run,
            parent=self.iface.mainWindow())

        #  # create action that will start plugin configuration
        # self.action = QAction(QIcon(":/plugins/interactive_map_tracking/icon_svg.svg"), "Interactive Map Tracking", self.iface.mainWindow())
        # self.action.setWhatsThis("Interactive Map Tracking")
        # QObject.connect(self.action, SIGNAL("triggered()"), self.run)
        # add toolbar button and menu item
        # self.iface.addToolBarIcon(self.action)

        self.init_plugin()

        # Connections
        # activate/desactivate plugin
        self.dlg.enablePlugin.clicked.connect(self.enabled_plugin)
        # activate/desactivate autosave
        self.dlg.enableAutoSave.clicked.connect(self.enabled_autosave)
        # activate/desactive tracking position
        self.dlg.enableTrackPosition.clicked.connect(self.enabled_trackposition)
        # box for tracking layers
        self.dlg.refreshLayersListForTrackPosition.clicked.connect(self.refreshComboBoxLayers)
        QObject.connect(self.dlg.trackingPositionLayerCombo, SIGNAL("currentIndexChanged ( const QString & )"),
                        self.currentIndexChangedTPLCB)
        QObject.connect(self.dlg.IMT_Window_Tabs, SIGNAL("currentChanged (int)"), self.QTabWidget_CurrentChanged)

        # Dev Debug
        self.dlg.enableLogging.clicked.connect(self.enableLogging)
        self.dlg.enableUseMutexForTP.clicked.connect(self.enableUseMutexForTP)

        # hide the window plugin
        # don't change the state (options) of the plugin
        self.dlg.buttonHide.clicked.connect(self.hide_plugin)
        #
        self.refreshComboBoxLayers()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Interactive Map Tracking'),
                action)
            self.iface.removeToolBarIcon(action)

    def onResizeEvent(self, event):
        # url: http://openclassrooms.com/forum/sujet/dimensionnement-automatique-d-une-qtabwidget
        QTabWidget.resizeEvent(self.dlg.IMT_Window_Tabs, event)
        # url: http://qt-project.org/doc/qt-4.8/qresizeevent.html
        self.dict_tabs_size[self.dlg.IMT_Window_Tabs.currentIndex()] = event.size()

    def run(self):
        """Run method that performs all the real work"""
        #
        # set the icon IMT ^^
        icon_path = ':/plugins/interactive_map_tracking/icon.png'
        self.dlg.setWindowIcon(QIcon(icon_path))

        # set the tab at init
        self.dlg.IMT_Window_Tabs.setCurrentIndex(0)
        # url: http://qt-project.org/doc/qt-4.8/qtabwidget.html#resizeEvent
        self.dlg.IMT_Window_Tabs.resizeEvent = self.onResizeEvent

        # show the dialog
        self.dlg.show()

        #
        self.enabled_plugin()

        # Run the dialog event loop
        self.dlg.exec_()

        # result = self.dlg.exec_()
        # # See if OK was pressed
        # if result:
        #     # Do something useful here - delete the line containing pass and
        #     # substitute with your code.
        #     pass

    def init_plugin(self):
        """ Init the plugin
        - Set defaults values in QSetting
        - Setup the GUI
        """

        qgis_log_tools.logMessageINFO("Launch 'init_plugin(...)' ...")

        s = QSettings()

        pluginEnable = s.value(self.qsettings_prefix_name + "enabledPlugin", defaultValue="undef")

        if pluginEnable == "undef":
            s.setValue(self.qsettings_prefix_name + "enabledPlugin", "false")
            s.setValue(self.qsettings_prefix_name + "enabledAutoSave", "false")
            s.setValue(self.qsettings_prefix_name + "enabledTrackPosition", "false")
            #
            s.setValue(self.qsettings_prefix_name + "threshold", str(self.threshold))
            #
            s.setValue(self.qsettings_prefix_name + "enabledLogging", "true")
            s.setValue(self.qsettings_prefix_name + "enableV2", "true")

        if s.value(self.qsettings_prefix_name + "enabledPlugin", "") == "true":
            self.update_checkbox(s, "enableAutoSave", self.dlg.enableAutoSave)
            self.update_checkbox(s, "enableTrackPosition", self.dlg.enableTrackPosition)
            #
            self.update_checkbox(s, "enableLogging", self.dlg.enableLogging)
            self.update_checkbox(s, "enableV2", self.dlg.enableUseMutexForTP)
            #
            self.dlg.thresholdLabel.setEnabled(True)
            self.dlg.threshold_extent.setEnabled(True)
            QObject.connect(self.dlg.threshold_extent, SIGNAL("returnPressed ()"), self.thresholdChanged)
        else:
            #
            self.dlg.enableAutoSave.setDisabled(True)
            self.dlg.enableAutoSave.setChecked(False)
            self.dlg.enableTrackPosition.setDisabled(True)
            self.dlg.enableTrackPosition.setChecked(False)
            #
            self.dlg.enableLogging.setDisabled(True)
            self.dlg.enableLogging.setChecked(True)
            self.dlg.enableUseMutexForTP.setDisabled(True)
            self.dlg.enableUseMutexForTP.setChecked(True)
            #
            self.dlg.thresholdLabel.setDisabled(True)
            self.dlg.threshold_extent.setDisabled(True)
            QObject.disconnect(self.dlg.threshold_extent, SIGNAL("returnPressed ()"), self.thresholdChanged)
            #
            QObject.disconnect(self.dlg.webView_about, SIGNAL("loadFinished (bool)"), self.webview_loadFinished)
            QObject.disconnect(self.dlg.webView_userdoc, SIGNAL("loadFinished (bool)"), self.webview_loadFinished)

    def update_checkbox(self, _settings, _name_in_setting, _checkbox):
        """ According to values stores in QSetting, update the state of a checkbox

        :param _settings: (local) Setting from Qt
        :type _settings: QSettings

        :param _name_in_setting: setting's name for the _checkbox in QSettings
        :type _name_in_setting: QString

        :param _checkbox: CheckBox to update state
        :type _checkbox: QCheckBox

        """
        if _settings.value(self.qsettings_prefix_name + _name_in_setting, "") == "true":
            _checkbox.setDisabled(False)
            _checkbox.setChecked(True)
        else:
            _checkbox.setDisabled(True)
            _checkbox.setChecked(False)

    def disconnectSignaleForLayerCrsChanged(self, layer):
        """ Disconnect the signal: 'layerCrsChanged' of the layer given

        :param layer:
        :return:
        """
        if None != layer and self.bSignalForLayerModifiedConnected:
            QObject.disconnect(layer, SIGNAL("layerCrsChanged()"), self.currentLayerCrsChanged)
            self.bSignalForLayerCrsChangedConnected = False
            #
            qgis_log_tools.logMessageINFO("Disconnect SIGNAL on layer: " + layer.name())

    def disconnectSignalForLayerModified(self, layer):
        """ Disconnect the signal: 'Layer Modified' of the layer given

        :param layer: QGIS Layer
        :type layer: QgsMapLayer

        """
        if None != layer and self.bSignalForLayerModifiedConnected:
            QObject.disconnect(layer, SIGNAL("layerModified()"), self.currentLayerModified)
            self.bSignalForLayerModifiedConnected = False
            #
            qgis_log_tools.logMessageINFO("Disconnect SIGNAL on layer: " + layer.name())

    def disconnectSignalForLayerChanged(self):
        """ Disconnect the signal: 'Current Layer Changed' of the QGIS Interface"""
        #
        if self.bSignalForLayerChangedConnected:
            QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer*)"),
                               self.qgisInterfaceCurrentLayerChanged)
            self.bSignalForLayerChangedConnected = False
            #
            qgis_log_tools.logMessageINFO("Disconnect SIGNAL on QGISInterface")

    def disconnectSignalForExtentsChanged(self):
        """ Disconnect the signal: 'Canvas Extents Changed' of the QGIS MapCanvas """
        #
        if self.bSignalForExtentsChangedConnected:
            self.iface.mapCanvas().extentsChanged.disconnect(self.canvasExtentsChanged)
            self.bSignalForExtentsChangedConnected = False
            #
            qgis_log_tools.logMessageINFO("Disconnect SIGNAL on QGISMapCanvas")

    def connectSignaleForLayerCrsChanged(self, layer):
        """ Disconnect the signal: 'layerCrsChanged' of the layer given

        :param layer:
        :return:
        """
        if None != layer and not self.bSignalForLayerCrsChangedConnected:
            QObject.connect(layer, SIGNAL("layerCrsChanged()"), self.currentLayerCrsChanged)
            self.bSignalForLayerCrsChangedConnected = False
            #
            qgis_log_tools.logMessageINFO("Connect SIGNAL on layer: " + layer.name())

    def connectSignalForLayerModified(self, layer):
        """ Connect the signal: "Layer Modified" to the layer given

        :param layer: QGIS layer
        :type layer: QgsMapLayer

        """
        if None != layer and not self.bSignalForLayerModifiedConnected:
            QObject.connect(layer, SIGNAL("layerModified()"), self.currentLayerModified)
            self.bSignalForLayerModifiedConnected = True
            #
            qgis_log_tools.logMessageINFO("Connect SIGNAL on layer: " + layer.name())

    def connectSignalForLayerChanged(self):
        """ Connect the signal: 'Layer Changed' to the layer given """
        #
        if not self.bSignalForLayerChangedConnected:
            QObject.connect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer*)"),
                            self.qgisInterfaceCurrentLayerChanged)
            self.bSignalForLayerChangedConnected = True
            #
            qgis_log_tools.logMessageINFO("Connect SIGNAL on QGISInterface")

    def connectSignalForExtentsChanged(self):
        """ Connect the signal: 'Extent Changed' to the QGIS MapCanvas """
        #
        if not self.bSignalForExtentsChangedConnected:
            self.iface.mapCanvas().extentsChanged.connect(self.canvasExtentsChanged)
            self.bSignalForExtentsChangedConnected = True
            #
            qgis_log_tools.logMessageINFO("Connect SIGNAL on QGISMapCanvas")

    def disconnectSignals(self, layer):
        """ Disconnect alls signals (of current layer & QGIS MapCanvas, Interface) """
        #
        qgis_log_tools.logMessageINFO("Disconnect all SIGNALS ...")
        #
        self.disconnectSignalForLayerModified(layer)
        self.disconnectSignalForLayerChanged()
        self.disconnectSignalForExtentsChanged()
        self.disconnectSignaleForLayerCrsChanged()
        #
        QObject.disconnect(self.dlg.webView_about, SIGNAL("loadFinished (bool)"), self.webview_loadFinished)
        QObject.disconnect(self.dlg.webView_userdoc, SIGNAL("loadFinished (bool)"), self.webview_loadFinished)

    def qgisInterfaceCurrentLayerChanged(self, layer):
        """ Action when the signal: 'Current Layer Changed' from QGIS MapCanvas is emitted&captured

        :param layer: QGIS layer -> current layer using by Interactive_Map_Tracking plugin
        :type layer: QgsMapLayer

        """
        # on deconnecte le layer courant
        if None != self.currentLayer:
            self.disconnectSignalForLayerModified(self.currentLayer)

        # Filtre sur les layers a "surveiller"
        if not qgis_layer_tools.filter_layer_for_imt(layer):
            layer = None

        if None != layer:
            self.currentLayer = layer
            #
            if self.dlg.enablePlugin.isChecked():
                if self.dlg.enableAutoSave.isChecked():
                    qgis_layer_tools.commitChangesAndRefresh(self.currentLayer, self.iface, QSettings())
                    self.connectSignalForLayerModified(self.currentLayer)

            qgis_log_tools.logMessageINFO("Change Layer: layer.name=" + layer.name())
        else:
            qgis_log_tools.logMessageINFO("No layer selected (for ITP)")

    def qgisInterfaceProjectRead(self):
        """ Action when the signal: 'Project Read' from QGIS Inteface is emitted&captured """
        pass

    def currentLayerModified(self):
        """ Action when the signal: 'Layer Modified' from QGIS Layer (current) is emitted&captured
        We connect a new signal: 'RenderComplete' to perform operation after the QGIS rendering (deferred strategy)

        """
        #
        if None != self.currentLayer:
            if None != self.iface.mapCanvas():
                QObject.connect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter*)"),
                                self.currentLayerModifiedAndRenderComplete)
                qgis_log_tools.logMessageINFO("Detect modification on layer:" + self.currentLayer.name())

    def currentLayerModifiedAndRenderComplete(self):
        """ Action when the signal: 'Render Complete' from QGIS Layer (current) is emitted&captured (after emitted&captured signal: 'Layer Modified') """
        #
        QObject.disconnect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter*)"),
                           self.currentLayerModifiedAndRenderComplete)
        #
        qgis_layer_tools.commitChangesAndRefresh(self.currentLayer, self.iface, QSettings())

    def canvasExtentsChanged(self):
        """ Action when the signal: 'Extent Changed' from QGIS MapCanvas is emitted&captured
         We connect a new signal: 'RenderComplete' to perform operation after the QGIS rendering (deferred strategy)

        """
        if self.bUseV2Functionnalities:
            # filter on our dummy refreshMap using little zoom on mapcanvas (=> canvasExtentChanged was emitted)
            if self.bRefreshMapFromAutoSave:
                self.bRefreshMapFromAutoSave = False
            else:
                self.update_track_position_with_qtimers()
        else:
            QObject.connect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter*)"),
                            self.canvasExtentsChangedAndRenderComplete)


    def canvasExtentsChangedAndRenderComplete(self):
        """ Action when the signal: 'Render Complete' from QGIS MapCanvas is emitted&captured (after a emitted&captured signal: 'Extent Changed')

        """
        #
        QObject.disconnect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter*)"),
                           self.canvasExtentsChangedAndRenderComplete)

        if self.bUseV2Functionnalities:
            self.update_track_position_with_qtimers()
        else:
            self.update_track_position()

    def filter_layer_for_tracking_position(layer):
        # set Attributes for Layer in DB
        # On récupère automatiquement le nombre de champs qui compose les features présentes dans ce layer
        # How to get field names in pyqgis 2.0
        # url: http://gis.stackexchange.com/questions/76364/how-to-get-field-names-in-pyqgis-2-0
        dataProvider = layer.dataProvider()

        # Return a map of indexes with field names for this layer.
        # url: http://qgis.org/api/classQgsVectorDataProvider.html#a53f4e62cb05889ecf9897fc6a015c296
        fields = dataProvider.fields()

        # get fields name from the layer
        field_names = [field.name() for field in fields]

        # find index for field 'user-id'
        id_user_id_field = imt_tools.find_index_field_by_name(field_names, "user_id")
        if id_user_id_field == -1:
            qgis_log_tools.logMessageWARNING(
                "No \"user_id\"::text field attributes found in layer: " + layer.name())
            return -1

        # find index for field 'writing_time'
        id_w_time_field = imt_tools.find_index_field_by_name(field_names, "w_time")
        if id_w_time_field == -1:
            qgis_log_tools.logMessageWARNING(
                "No \"w_time\"::text attributes found in layer: " + layer.name())
            return -1

        return [id_user_id_field, id_w_time_field]

    def currentIndexChangedTPLCB(self, layer_name):
        """

        :param layer_name:
        :return:

        """
        qgis_log_tools.logMessageINFO("Launch 'currentIndexChangedTPLCB(self, layer_name=" + layer_name + ")' ...")
        # layer_name == "" when when we clear the combobox (for example)
        if layer_name == "":
            return

        layer_for_tp = imt_tools.find_layer_in_qgis_legend_interface(self.iface, layer_name)
        self.currentLayerForTrackingPosition = layer_for_tp  # set the layer for tracking position (plugin)

        list_id_fields = qgis_layer_tools.filter_layer_trackingposition_required_fields(layer_for_tp)

        self.tp_id_user_id = list_id_fields[0]
        self.tp_id_w_time = list_id_fields[1]

        dataProvider = layer_for_tp.dataProvider()

        # Return a map of indexes with field names for this layer.
        # url: http://qgis.org/api/classQgsVectorDataProvider.html#a53f4e62cb05889ecf9897fc6a015c296
        fields = dataProvider.fields()

        # set the fields
        # reset all fields in None
        self.values = [None for i in range(fields.count())]
        # set user_id field (suppose constant for a layer (in QGIS session))
        self.values[self.tp_id_user_id] = self.tp_user_name

    def refreshComboBoxLayers(self):
        """ Action when the Combo Box attached to refreshing layers for tracking position is clicked """
        #
        qgis_log_tools.logMessageINFO("Launch 'refreshComboBoxLayers(...)' ...")

        self.dlg.trackingPositionLayerCombo.clear()

        idComboBoxIndex = -1
        idComboBoxForDefaultSearchLayer = -1

        # search a default layer ('camera_position') if no layer was selected before
        # else we search the same layer (if it present)
        if self.currentLayerForTrackingPosition is None:
            defaultSearchLayer = "camera_position"
        else:
            defaultSearchLayer = self.currentLayerForTrackingPosition.name()

        # dictionnary to link id on combobox and objects QGIS layer
        dict_key_comboboxindex_value_layer = {}
        #
        layers = QgsMapLayerRegistry.instance().mapLayers().values()
        for layer in layers:
            # filter on layers to add in combobox
            if qgis_layer_tools.filter_layer_for_trackingposition(layer):

                idComboBoxIndex = self.dlg.trackingPositionLayerCombo.count()
                dict_key_comboboxindex_value_layer[idComboBoxIndex] = layer
                self.dlg.trackingPositionLayerCombo.addItem(layer.name(), layer)

                # default search layer
                if layer.name() == defaultSearchLayer:
                    idComboBoxForDefaultSearchLayer = idComboBoxIndex
                    #
                    qgis_log_tools.logMessageINFO(
                        defaultSearchLayer + " layer found - id in combobox: " +
                        str(idComboBoxForDefaultSearchLayer)
                    )

        # update GUI
        if idComboBoxForDefaultSearchLayer != -1:
            self.dlg.trackingPositionLayerCombo.setCurrentIndex(idComboBoxForDefaultSearchLayer)
            idComboBoxIndex = idComboBoxForDefaultSearchLayer

        if idComboBoxIndex != -1:
            try:
                self.currentLayerForTrackingPosition = dict_key_comboboxindex_value_layer[idComboBoxIndex]
                qgis_log_tools.logMessageINFO("Set the layer to: " + self.currentLayerForTrackingPosition.name())
            except:
                qgis_log_tools.logMessageINFO("!!! ERROR for selecting layer !!!")

    def enabled_autosave(self):
        """ Action when the checkbox 'Enable Auto-Save and Refresh' is clicked """
        #
        qgis_log_tools.logMessageINFO("Launch 'enable_autosave(...)' ...")

        resultCommit = False

        # filtre sur les layers
        if qgis_layer_tools.filter_layer_for_imt(self.iface.activeLayer()):
            self.currentLayer = self.iface.activeLayer()
        else:
            self.currentLayer = None

        #
        if self.dlg.enableAutoSave.isChecked():
            #
            resultCommit = qgis_layer_tools.commitChangesAndRefresh(self.currentLayer, self.iface, QSettings())
            #
            self.connectSignalForLayerModified(self.currentLayer)
        else:
            self.disconnectSignalForLayerModified(self.currentLayer)
        #
        return resultCommit

    def stop_threads(self):
        if self.qtimer_tracking_position_rtt_to_memory.isActive():
            self.qtimer_tracking_position_rtt_to_memory.stop()
        if self.qtimer_tracking_position_memory_to_geom.isActive():
            self.qtimer_tracking_position_memory_to_geom.stop()
        if self.qtimer_tracking_position_geom_to_layer.isActive():
            self.qtimer_tracking_position_geom_to_layer.stop()
        if self.qtimer_tracking_position_layers_to_commit.isActive():
            self.qtimer_tracking_position_layers_to_commit.stop()

    def enabled_trackposition(self):
        """ Action when the checkbox 'Enable Tracking Position' is clicked """
        #
        qgis_log_tools.logMessageINFO("Launch 'enable_trackposition(...)' ...")

        if self.dlg.enableTrackPosition.isChecked():
            #
            self.refreshComboBoxLayers()
            #
            self.connectSignalForExtentsChanged()
        else:
            self.disconnectSignalForExtentsChanged()

            self.stop_threads()

    def enableLogging(self):
        """ Action when the checkbox 'Enable LOGging' is clicked """
        #
        qgis_log_tools.setLogging(self.dlg.enableLogging.isChecked())

    def enableUseMutexForTP(self):
        """ Action when the checkbox 'Use Mutex (for TrackingPosition) [BETA]' is clicked
        Beta test for:
        - using Mutex to protect commitChange operation in multi-threads context (signals strategy)
        - using queuing requests from TrackPosition (we try to amortize the cost and effects on QGIS GUI)

        """
        self.bUseV2Functionnalities = self.dlg.enableUseMutexForTP.isChecked()

        if not(self.dlg.enableUseMutexForTP.isChecked() and self.dlg.enableTrackPosition.isChecked()):
            self.stop_threads()

    def enabled_plugin(self):
        """ Action when the checkbox 'Enable SteetGen3 Plugin' is clicked
        Activate/desactivate all options/capabilities of IMT plugin: AutoSave&Refresh, TrackPosition

        """
        qgis_log_tools.logMessageINFO("Launch 'enabled_plugin(...)' ...")

        resultCommit = False

        # filtre sur les layers a prendre en compte
        if qgis_layer_tools.filter_layer_postgis(self.iface.activeLayer()):
            self.currentLayer = self.iface.activeLayer()
        else:
            self.currentLayer = None

        if self.dlg.enablePlugin.isChecked():
            #
            self.dlg.enableAutoSave.setEnabled(True)
            self.dlg.enableTrackPosition.setEnabled(True)
            self.dlg.enableLogging.setEnabled(True)
            self.dlg.thresholdLabel.setEnabled(True)
            self.dlg.threshold_extent.setEnabled(True)
            QObject.connect(self.dlg.threshold_extent, SIGNAL("editingFinished ()"), self.thresholdChanged)
            self.dlg.enableUseMutexForTP.setEnabled(True)
            #
            self.connectSignalForLayerChanged()
            if self.dlg.enableAutoSave.isChecked():
                self.connectSignalForLayerModified(self.currentLayer)
                resultCommit = qgis_layer_tools.commitChangesAndRefresh(self.currentLayer, self.iface, QSettings())
            if self.dlg.enableTrackPosition.isChecked():
                self.refreshComboBoxLayers()
                self.connectSignalForExtentsChanged()
        else:
            self.dlg.enableAutoSave.setDisabled(True)
            self.dlg.enableTrackPosition.setDisabled(True)
            self.dlg.enableLogging.setDisabled(True)
            self.dlg.thresholdLabel.setDisabled(True)
            self.dlg.threshold_extent.setDisabled(True)
            QObject.disconnect(self.dlg.threshold_extent, SIGNAL("returnPressed ()"), self.thresholdChanged)
            self.dlg.enableUseMutexForTP.setDisabled(True)
            #
            self.disconnectSignalForLayerChanged()
            if self.dlg.enableAutoSave.isChecked():
                self.disconnectSignalForLayerModified(self.currentLayer)
            if self.dlg.enableTrackPosition.isChecked():
                self.disconnectSignalForExtentsChanged()

                self.stop_threads()

        return resultCommit

    def update_setting(self, _s, _name_in_setting, _checkbox):
        """ Update the value store in settings (Qt settings) according to checkbox (Qt) status

        :param _s: Qt Settings
        :type _s: QSettings

        :param _name_in_setting: Name of the setting in QSetting
        :type _name_in_setting: QString

        :param _checkbox: CheckBox link to this setting
        :type _checkbox: QCheckBox

        """
        if _checkbox.isChecked():
            _s.setValue(self.qsettings_prefix_name + _name_in_setting, "true")
        else:
            _s.setValue(self.qsettings_prefix_name + _name_in_setting, "false")

    def update_settings(self, _s):
        """ Update all settings

        :param _s: Qt Settings
        :type _s: QSettings

        """
        dlg = self.dlg
        # Update (Qt) settings according to the GUI IMT plugin
        self.update_setting(_s, "enabledPlugin", dlg.enablePlugin)
        self.update_setting(_s, "enablesAutoSave", dlg.enableAutoSave)
        self.update_setting(_s, "enablesTrackPosition", dlg.enableTrackPosition)

    def hide_plugin(self):
        """ Hide the plugin.
        Don't change the state of the plugin

        """
        self.update_settings(QSettings())
        self.dlg.hide()

    def thresholdChanged(self):
        """
        QT Line edit changed, we get/interpret the new value (if valid)
        Format for threshold scale : 'a'[int]:'b'[int]
        We just used 'b' for scale => threshold_scale = 'b'
        """
        validFormat = True

        try:
            threshold_string = self.dlg.threshold_extent.text()
            self.threshold = int(threshold_string)
        except ValueError:
            try:
                a, b = threshold_string.split(":")
                try:
                    int(a)  # just to verify the type of 'a'
                    self.threshold = int(b)  # only use 'b' to change the threshold scale value
                except Exception:
                    validFormat = False  # problem with 'a'
            except Exception:
                validFormat = False  # problem with 'b'
        # Input format problem!
        if validFormat == False:
            qgis_log_tools.logMessageWARNING("Invalid input for scale! Scale format input : [int]:[int] or just [int]")

        # just for visualisation purpose
        self.dlg.threshold_extent.setText("1:" + str(self.threshold))

    def update_size_dlg_from_frame(self, dlg, frame, margin_width=60):
        width = frame.contentsSize().width()
        height = frame.contentsSize().height()
        #
        width += margin_width
        #
        width = max(1024, width)
        height = min(768, max(height, width*4/3))
        #
        dlg.resize(width, height)
        #
        return width, height

    def update_size_dlg_from_tuple(self, dlg, tuple):
        dlg.resize(tuple.width, tuple.height)
        return tuple.width, tuple.height

    def webview_loadFinished(self, ok):
        webview = self.current_webview

        tuple_webview = self.webview_dict.setdefault(webview, self.webview_default_tuple)
        last_state = tuple_webview.state
        QgsMessageLog.logMessage("#last_state : " + str(last_state))

        if ok:
            # we have loaded a HTML page (offline or online)
            QgsMessageLog.logMessage("## WebView : OK")

            # update the QDiaglog sizes
            width, height = self.update_size_dlg_from_frame(
                self.dlg,
                webview.page().currentFrame(),
                self.webview_margin
            )
            # update the tuple for this webview
            self.webview_dict[webview] = self.TP_NAMEDTUPLE_WEBVIEW(
                1,
                width, height,
                tuple_webview.online_url,
                tuple_webview.offline_url
            )
            #
            QgsMessageLog.logMessage("### width : " + str(width) + " - height : " + str(height))
        else:
            QgsMessageLog.logMessage("## WebView : FAILED TO LOAD")
            #
            self.webview_dict[webview] = self.TP_NAMEDTUPLE_WEBVIEW(
                2,
                tuple_webview.width, tuple_webview.height,
                tuple_webview.online_url,
                tuple_webview.offline_url
            )
            # try to load the offline version (still in initial state)
            webview.load(QUrl(tuple_webview.offline_url))

    def adapt_qdialog_size_to_webview(self, webview, margin=60):
        """

        :param webview:
        :param margin:
        :return:
        """
        #
        tuple_webview = self.webview_dict.setdefault(webview, self.webview_default_tuple)

        self.webview_margin = margin
        self.current_webview = webview

        # signal : 'loadFinished(bool)'
        QObject.connect(webview, SIGNAL("loadFinished (bool)"), self.webview_loadFinished)

        if tuple_webview.state == 2:    # offline
            webview.load(QUrl(tuple_webview.offline_url))
        else:   # 0 or 1 (init, online)
            webview.load(QUrl(tuple_webview.online_url))

    def restore_dlg_size(self):
        self.dlg.resize(self.dlg_size)

    def QTabWidget_CurrentChanged(self, index):

        QObject.disconnect(self.dlg.webView_about, SIGNAL("loadFinished (bool)"), self.webview_loadFinished)
        QObject.disconnect(self.dlg.webView_userdoc, SIGNAL("loadFinished (bool)"), self.webview_loadFinished)

        if index == 3:
            QgsMessageLog.logMessage("## Tab : User Doc")
            self.adapt_qdialog_size_to_webview(self.dlg.webView_userdoc, 60)
        elif index == 4:
            QgsMessageLog.logMessage("## Tab : About")
            self.adapt_qdialog_size_to_webview(self.dlg.webView_about, 60)
        else:
            self.dict_tabs_size[index] = self.dict_tabs_size.setdefault(index, self.dlg.minimumSize())
            self.dlg.resize(self.dict_tabs_size[index])

    # TODO: optimize update_track_position because it's a (critical) real-time method !
    def update_track_position(self, bWithProjectionInCRSLayer=True, bUseEmptyFields=False):
        """ Perform the update tracking position (in real-time)
        Save the current Qgis Extent (+metadatas) into a QGIS vector layer (compatible for tracking position).
        The QGIS Vector Layer need at least 2 attributes:
            - user_id: text
            - w_time: text

        :param bWithProjectionInCRSLayer: Option [default=True].
         If True, project the QGIS MapCanvas extent (QGIS World CRS) into Layer CRS (CRS=Coordinates Reference System)
        :type bWithProjectionInCRSLayer: bool

        :param bUseEmptyFields: Option [default=False]
         If True, don't set fields (user_id, w_time)
         If False, use a auto-generate id for user (user-name from OS + IP Lan) and current date time (from time stamp os into QDateTime string format)
        :type bUseEmptyFields: bool

        """

        if self.currentLayerForTrackingPosition is None:
            return -1

        mapCanvas = self.iface.mapCanvas()
        mapcanvas_extent = mapCanvas.extent()

        layer_for_polygon_extent = self.currentLayerForTrackingPosition

        # # filter on extent size
        # try:
        # threshold = int(self.dlg.threshold_extent.text())
        # except Exception:
        #     qgis_log_tools.logMessageWARNING("Threshold can only be a number")
        #     return -1

        # if max(mapcanvas_extent.width(), mapcanvas_extent.height()) > threshold:
        if mapCanvas.scale() > self.threshold:
            qgis_log_tools.logMessageWARNING("MapCanvas extent size exceed the Threshold size for tracking")
            qgis_log_tools.logMessageWARNING(
                "-> MapCanvas extent size= " + str(max(mapcanvas_extent.width(), mapcanvas_extent.height())) +
                "\tThreshold size= " + str(self.threshold))
            return -2

        # get the list points from the current extent (from QGIS MapCanvas)
        list_points_from_mapcanvas = imt_tools.construct_listpoints_from_extent(mapcanvas_extent)

        ## NEED TO OPTIMIZE ##
        if bWithProjectionInCRSLayer:
            # url: http://qgis.org/api/classQgsMapCanvas.html#af0ffae7b5e5ec8b29764773fa6a74d58
            extent_src_crs = mapCanvas.mapSettings().destinationCrs()
            # url: http://qgis.org/api/classQgsMapLayer.html#a40b79e2d6043f8ec316a28cb17febd6c
            extent_dst_crs = layer_for_polygon_extent.crs()
            # url: http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/crs.html
            xform = QgsCoordinateTransform(extent_src_crs, extent_dst_crs)
            #
            list_points = [xform.transform(point) for point in list_points_from_mapcanvas]
        else:
            list_points = list_points_from_mapcanvas
        ## NEED TO OPTIMIZE ##

        # list of lists of points
        gPolygon = QgsGeometry.fromPolygon([list_points])

        fet = QgsFeature()

        fet.setGeometry(gPolygon)

        if bUseEmptyFields:
            pass
        else:
            # update the time stamp attribute
            self.values[self.tp_id_w_time] = imt_tools.get_timestamp_from_qt_string_format()

        fet.setAttributes(self.values)

        # How can I programatically create and add features to a memory layer in QGIS 1.9?
        # url: http://gis.stackexchange.com/questions/60473/how-can-i-programatically-create-and-add-features-to-a-memory-layer-in-qgis-1-9
        # write the layer and send request to DB
        layer_for_polygon_extent.startEditing()
        layer_for_polygon_extent.addFeatures([fet], False)  # bool_makeSelected=False
        #
        resultCommit = layer_for_polygon_extent.commitChanges()
        #
        if resultCommit:
            qgis_log_tools.logMessageINFO("Location saved in layer: " + layer_for_polygon_extent.name())
        else:
            qgis_log_tools.logMessageCRITICAL(
                "saving position failed : are you sure the selected tracking layer: " + layer_for_polygon_extent.name() +
                "has at least 2 attributes : \"user_id\"::text and \"w_time\"::text")

            commitErrorString = layer_for_polygon_extent.commitErrors()[2]
            commitErrorStringShort = commitErrorString[commitErrorString.rfind(":") + 2:len(
                commitErrorString)]  # +2 to skip ': ' prefix of commitError msg
            self.iface.messageBar().pushMessage("IMT. ERROR : " + "\"" + commitErrorStringShort + "\"",
                                                "",
                                                QgsMessageBar.CRITICAL, 0)
        #
        return resultCommit

    def update_track_position_with_qtimers(self, bWithProjectionInCRSLayer=True, bUseEmptyFields=False):
        """
        Note: it's not a Thread/QTimer

        :param bWithProjectionInCRSLayer:
        :param bUseEmptyFields:
        :return:
        """

        bIsTimeToUpdate = self.tp_timers.is_time_to_update("update_track_position_with_qtimers", "tp_threshold_time_for_realtime_tracking_position")
        if bIsTimeToUpdate:
            # Do we have a current layer activate for tracking position ?
            if self.currentLayerForTrackingPosition is None:
            # if not, no need to go further
                return -1

            mapCanvas = self.iface.mapCanvas()
            mapcanvas_extent = mapCanvas.extent()

            # Filter on extent map scale (size)
            # We use a threshold scale (user input in the GUI)
            if mapCanvas.scale() > self.threshold:
                qgis_log_tools.logMessageWARNING("MapCanvas extent scale exceed the Threshold scale for tracking")
                qgis_log_tools.logMessageWARNING(
                    "-> MapCanvas scale= " + str(mapCanvas.scale()) +
                    "\tThreshold scale= " + str(self.threshold))
                return -2

            layer_for_itp = self.currentLayerForTrackingPosition

            # Build the tuple contains:
            # - layer used for tracking position
            # - list of points extract from the current extent for QGIS Map Canvas
            # - acquisition time for this track
            rt_ntuple = self.TP_NAMEDTUPLE_LET(
                layer_for_itp,
                imt_tools.construct_listpoints_from_extent(mapcanvas_extent),
                imt_tools.get_timestamp()
            )

            self.tp_timers.update("update_track_position_with_qtimers")

            # This queue is not protect (multi-threads context)
            # but it's oki in your case
            # queue in write-append only here !
            self.tp_queue_rt_ntuples_let.put(rt_ntuple)

            interval = self.tp_timers.get_delay("tp_threshold_time_for_tp_to_mem")
            self.qtimer_tracking_position_rtt_to_memory.start(interval)

        # update timer for still moving here !
        self.tp_timers.update("still moving")

        return 1

    def tracking_position_qtimer_rttp_to_memory(self):
        """ Action perform when the QTimer for Tracking Position is time out
        Enqueue requests from Tracking Position to amortize the cost&effect on QGIS GUI

        This pass transfer events inputs map moving into memory (QGIS -> Python)
        """
        qgis_log_tools.logMessageINFO("~~ CALL : tracking_position_qtimer_rttp_to_memory ~~")

        # qgis_log_tools.logMessage("self.tp_timers.delta_with_current_time('tp_time_last_rttp_to_mem'): "
        #                           + str(self.tp_timers.delta_with_current_time("tp_time_last_rttp_to_mem")))

        # bIsTimeToUpdate = self.tp_timers.is_time_to_update("tp_time_last_rttp_to_mem",
        #                                                    "tp_threshold_time_for_tp_to_mem")

        size_tp_queue = self.tp_queue_rt_ntuples_let.qsize()

        # this queue is not protect (multi-threads context)
        # but it's oki in your case
        while not self.tp_queue_rt_ntuples_let.empty():
            # queue in read-write-delete/pop here
            tp_tuple = self.tp_queue_rt_ntuples_let.get()
            self.tp_queue_rt_ntuples_let.task_done()

            # url: http://stackoverflow.com/questions/20585920/how-to-add-multiple-values-to-a-dictionary-key-in-python
            self.tp_dict_key_l_values_et.setdefault(tp_tuple.layer, []).append(
                self.TP_NAMEDTUPLE_ET(tp_tuple.extent, tp_tuple.w_time)
            )

        if size_tp_queue != 0:
            # update timer
            # self.tp_timers.update("tp_time_last_rttp_to_mem")
            #
            qgis_log_tools.logMessageINFO("** Pack " + str(size_tp_queue) + " tuples for 1 call -> mem")

        #####################
        # Process Management
        #####################
        self.qtimer_tracking_position_rtt_to_memory.stop()
        #
        interval = self.tp_timers.get_delay("tp_threshold_time_for_construct_geom")
        self.qtimer_tracking_position_memory_to_geom.start(interval)
        #####################

    def tracking_position_qtimer_memory_to_geom(self):
        """ Action perform when the QTimer for Tracking Position is time out
        Enqueue requests from Tracking Position to amortize the cost&effect on QGIS GUI

        This pass convert tracking extents datas (MEMory side) to QGIS GEOMetries (MEMory side)
        In this pass we project the entries points in world (QGIS) CRS into CRS of the layer target (for tracking position)
        """
        qgis_log_tools.logMessageINFO("~~ CALL : tracking_position_qtimer_memory_to_geom ~~")

        # qgis_log_tools.logMessage("self.tp_timers.delta_with_current_time('tp_time_last_rttp_to_mem'): "
        #                           + str(self.tp_timers.delta_with_current_time("tp_time_last_rttp_to_mem")))

        # bIsTimeToUpdate = self.tp_timers.is_time_to_update("tp_time_last_rttp_to_mem",
        #                                                    "tp_threshold_time_for_construct_geom")

        mapCanvas = self.iface.mapCanvas()

        # url: http://qgis.org/api/classQgsMapCanvas.html#af0ffae7b5e5ec8b29764773fa6a74d58
        extent_src_crs = mapCanvas.mapSettings().destinationCrs()

        append_in_dic = False
        for layer in self.tp_dict_key_l_values_et.keys():
            layer_to_commit = layer

            # url: http://qgis.org/api/classQgsMapLayer.html#a40b79e2d6043f8ec316a28cb17febd6c
            extent_dst_crs = layer_to_commit.crs()
            # url: http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/crs.html
            xform = QgsCoordinateTransform(extent_src_crs, extent_dst_crs)

            tp_list_fets = []

            # pop key from tracking position dictionary
            list_ntuples = self.tp_dict_key_l_values_et.pop(layer)
            append_at_least_1_fet = False
            for tp_namedtuple in list_ntuples:
                mapcanvas_extent = tp_namedtuple.extent

                w_time = tp_namedtuple.w_time

                # get the list points from the current extent (from QGIS MapCanvas)
                list_points_from_mapcanvas = mapcanvas_extent

                # TODO: add a option for this feature (Projected points in CRS destination layer) in GUI
                bWithProjectionInCRSLayer = True
                if bWithProjectionInCRSLayer:
                    #
                    list_points = [xform.transform(point) for point in list_points_from_mapcanvas]
                else:
                    list_points = list_points_from_mapcanvas

                # list of lists of points
                gPolygon = QgsGeometry.fromPolygon([list_points])

                fet = QgsFeature()

                fet.setGeometry(gPolygon)

                # update the time stamp attribute
                self.values[self.tp_id_w_time] = imt_tools.convert_timestamp_to_qt_string_format(w_time)

                fet.setAttributes(self.values)

                tp_list_fets.append(fet)
                append_at_least_1_fet = True

            if append_at_least_1_fet:
                self.tp_dict_key_l_values_listfeatures.setdefault(layer, []).append(tp_list_fets)
                append_in_dic = True
                qgis_log_tools.logMessageINFO(
                    "-- Pack " + str(len(tp_list_fets)) + " features in layer: " + layer.name())

        if append_in_dic:

            # update timer
            # self.tp_timers.update("tp_time_last_construct_geom")

            #####################
            # Process Management
            #####################
            #
            self.qtimer_tracking_position_memory_to_geom.stop()
            #
            interval = self.tp_timers.get_delay("tp_threshold_time_for_sending_geom_to_layer")
            interval += CONVERT_S_TO_MS(max(0.0, (self.tp_timers.get_delay("delay_time_still_moving")-self.tp_timers.delta_with_current_time("still moving"))))
            self.qtimer_tracking_position_geom_to_layer.start(interval)
            #####################

            # qgis_log_tools.logMessage("=> still moving = " + str(self.tp_timers.get_delay("delay_time_still_moving")-self.tp_timers.delta_with_current_time("still moving")))
            # qgis_log_tools.logMessage("=> still moving = " + str(max(0.0, self.tp_timers.get_delay("delay_time_still_moving")-self.tp_timers.delta_with_current_time("still moving"))))
            # qgis_log_tools.logMessage("delay= " + str(delay))

    def tracking_position_qtimer_geom_to_layer(self):
        """ Action perform when the QTimer for Tracking Position is time out
        Enqueue requests from Tracking Position to amortize the cost&effect on QGIS GUI

        In this pass we transfer if timeout for delay is done and we 'not moving' on QGIS Map
        QGIS GEOmetries [MEM] into target Layer [MEM]
        This operation send/render geometries into the Layer (we see a rectangle representation of our extent on the screen)
        """
        qgis_log_tools.logMessageINFO("~~ CALL : tracking_position_qtimer_geom_to_layer ~~")

        bNotMovingOnQGISMap = self.tp_timers.is_time_to_update("still moving", "delay_time_still_moving")

        # qgis_log_tools.logMessage("self.tp_timers.delta_with_current_time('still moving'): " + str(self.tp_timers.delta_with_current_time("still moving")))
        # qgis_log_tools.logMessage("bNotMovingOnQGISMap: " + str(bNotMovingOnQGISMap))
        # qgis_log_tools.logMessage("delay_time_still_moving: " + str(self.tp_timers.get_delay("delay_time_still_moving")))

        # if bIsTimeToUpdate and bNotMovingOnQGISMap:
        if bNotMovingOnQGISMap:
            append_in_dict_one_time = False

            for layer in self.tp_dict_key_l_values_listfeatures.keys():
                # from the dict we retrieve a list of list
                tp_list_of_list_fets = self.tp_dict_key_l_values_listfeatures.pop(layer)

                # How can I programatically create and add features to a memory layer in QGIS 1.9?
                # url: http://gis.stackexchange.com/questions/60473/how-can-i-programatically-create-and-add-features-to-a-memory-layer-in-qgis-1-9
                # write the layer and send request to DB
                layer.startEditing()
                for tp_list_fets in tp_list_of_list_fets:
                    layer.addFeatures(tp_list_fets, False)  # bool_makeSelected=False

                self.tp_dict_layers_to_commit[layer] = 1
                append_in_dict_one_time = True

                qgis_log_tools.logMessageINFO(
                    "++ Pack requests => " + str(len(tp_list_of_list_fets)) + " extents for layer: " + layer.name())

            if append_in_dict_one_time:
                # update timer
                # self.tp_timers.update("tp_time_last_send_geom_to_layer")

                #####################
                # Process Management
                #####################
                self.qtimer_tracking_position_geom_to_layer.stop()
                #
                interval = self.tp_timers.get_delay("tp_threshold_time_for_sending_layer_to_dp")
                interval += CONVERT_S_TO_MS(max(0.0, self.tp_timers.get_delay("delay_time_still_moving")-self.tp_timers.delta_with_current_time("still moving")))
                self.qtimer_tracking_position_layers_to_commit.start(interval)
                #####################

                # qgis_log_tools.logMessageINFO("tp_threshold_time_for_sending_layer_to_dp= " + str(self.tp_timers.get_delay("tp_threshold_time_for_sending_layer_to_dp")))
        else:
            self.qtimer_tracking_position_geom_to_layer.setInterval(self.tp_timers.get_delay("delay_time_still_moving")*1000)

    def tracking_position_qtimer_layers_to_commit(self):
        """Action perform when the QTimer for Tracking Position is time out
         Enqueue requests from Tracking Position to amortize the cost&effect on QGIS GUI

         In this pass, we commit QGIS Layer into Data Provider (PostGIS DataBase, or ShapeFile, or anything (local or distant)
         MEM -> DP
         """
        qgis_log_tools.logMessageINFO("~~ CALL : tracking_position_qtimer_layers_to_commit ~~")

        bNotMovingOnQGISMap = self.tp_timers.is_time_to_update("still moving", "delay_time_still_moving")

        # qgis_log_tools.logMessage("self.tp_timers.delta_with_current_time(''tp_time_last_send_geom_to_layer''):"+str(self.tp_timers.delta_with_current_time("tp_time_last_send_geom_to_layer")))
        # qgis_log_tools.logMessage("bNotMovingOnQGISMap: " + str(bNotMovingOnQGISMap))

        if bNotMovingOnQGISMap:
            layers = self.tp_dict_layers_to_commit.keys()
            # clear dict
            self.tp_dict_layers_to_commit.clear()

            for layer_to_commit in layers:
                #
                try:
                    # update timer
                    # self.tp_timers.update("tracking_position_qtimer_layers_to_commit")

                    resultCommit = layer_to_commit.commitChanges()

                    if resultCommit:
                        qgis_log_tools.logMessageINFO("* Commit change layer:" + layer_to_commit.name + " [OK]")
                except:
                    # TODO : deal with errors/exceptions
                    pass

            #####################
            # Process Management
            #####################
            # last link of processes chain
            self.qtimer_tracking_position_layers_to_commit.stop()
            #####################
        else:
            #####################
            # Process Management
            #####################
            interval = CONVERT_S_TO_MS(self.tp_timers.get_delay("delay_time_still_moving"))
            self.qtimer_tracking_position_layers_to_commit.setInterval(interval)
            #####################


def tracking_position_log_threads_infos(self):
    """
    DEBUG INFORMATIONS
    """
    qgis_log_tools.logMessageINFO(
        "self.tp_queue_rt_ntuples_let.qsize(): " + str(self.tp_queue_rt_ntuples_let.qsize()))
    qgis_log_tools.logMessageINFO(
        "- self.tp_dict_key_l_values_et.qsize(): " + str(len(self.tp_dict_key_l_values_et)))
    qgis_log_tools.logMessageINFO("- - self.tp_list_fets: " + str(len(self.tp_list_fets)))
    qgis_log_tools.logMessageINFO(
        "- - - self.tp_dict_key_l_values_listfeatures: " + str(len(self.tp_dict_key_l_values_listfeatures)))
    qgis_log_tools.logMessageINFO(
        "- - - - self.tp_list_layers_to_commit: " + str(len(self.tp_dict_layers_to_commit)))
