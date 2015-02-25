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
from PyQt4.QtCore import QObject, SIGNAL
from PyQt4.QtCore import QMutexLocker, QMutex
from PyQt4.QtGui import QAction, QIcon

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


class interactive_map_tracking:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
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
        self.bSignalForLayerCrsChangedConnected = False

        self.idCameraPositionLayerInBox = 0

        self.bSignalForProjectReadConnected = True
        QObject.connect(self.iface, SIGNAL("projectRead()"), self.qgisInterfaceProjectRead)

        # MUTEX
        self.bUseMutexAndBetaFunctionalities = self.dlg.enableUseMutexForTP.isChecked()
        self.QMCanvasExtentsChanged = QMutex()
        self.QMCanvasExtentsChangedAndRenderComplete = QMutex()

        self.trackposition_queue = Queue.LifoQueue()
        self.cron_trackposition = QTimer()
        self.cron_trackposition.timeout.connect(self.cronTrackPositionEvent)
        self.cron_trackposition_delay = 2000    # 2000ms = 2s

        # user-id:
        # from user id OS
        os_username = imt_tools.get_os_username()
        # try to use IP to identify the user
        user_ip = imt_tools.get_lan_ip()
        #
        self.trackposition_user_name = os_username + " (" + user_ip + ")"

        self.threshold = 200

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
        self.add_action(
            icon_path,
            text=self.tr(u'Tools for Interactive Map Tracking'),
            callback=self.run,
            parent=self.iface.mainWindow())

        self.init_plugin()

        # Connections
        # activate/desactivate plugin
        self.dlg.enablePlugin.clicked.connect(self.enabled_plugin)
        # activate/desactivate autosave
        self.dlg.enableAutoSave.clicked.connect(self.enabled_autosave)
        # activate/desactive tracking position
        self.dlg.enableTrackPosition.clicked.connect(self.enabled_trackposition)
        self.dlg.refreshLayersListForTrackPosition.clicked.connect(self.refreshComboBoxLayers)

        self.dlg.enableLogging.clicked.connect(self.enableLogging)
        self.dlg.enableUseMutexForTP.clicked.connect(self.enableUseMutexForTP)

        # hide the window plugin
        # don't change the state (options) of the plugin
        self.dlg.buttonHide.clicked.connect(self.hide_plugin)
        #
        self.idCameraPositionLayerInBox = 0
        self.refreshComboBoxLayers()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Interactive Map Tracking'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""
        #
        # set the icon IMT ^^
        icon_path = ':/plugins/interactive_map_tracking/icon.png'
        self.dlg.setWindowIcon(QIcon(icon_path))

        # fix the size of the pluging window
        self.dlg.setFixedSize(self.dlg.size())

        # set the tab at init
        self.dlg.IMT_Window_Tabs.setCurrentIndex(0)

        # show the dialog
        self.dlg.show()

        #
        self.enabled_plugin()

        # Run the dialog event loop
        result = self.dlg.exec_()

        self.cron_trackposition.stop()

        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

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
            s.setValue(self.qsettings_prefix_name + "enabledLogging", "false")
            s.setValue(self.qsettings_prefix_name + "threshold", "200")

        if s.value(self.qsettings_prefix_name + "enabledPlugin", "") == "true":
            self.update_checkbox(s, "enableAutoSave", self.dlg.enableAutoSave)
            self.update_checkbox(s, "enableTrackPosition", self.dlg.enableTrackPosition)
            self.update_checkbox(s, "enableLogging", self.dlg.enableLogging)
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
            self.dlg.enableLogging.setDisabled(True)
            self.dlg.enableLogging.setChecked(False)
            self.dlg.enableUseMutexForTP.setDisabled(True)
            self.dlg.enableUseMutexForTP.setChecked(False)
            #
            self.dlg.thresholdLabel.setDisabled(True)
            self.dlg.threshold_extent.setText("1:200")
            self.threshold = 200
            self.dlg.threshold_extent.setDisabled(True)
            QObject.disconnect(self.dlg.threshold_extent, SIGNAL("returnPressed ()"), self.thresholdChanged)

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
            qgis_log_tools.logMessageINFO("No layer selected")

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
        self.commitChangesAndRefresh()

    def canvasExtentsChanged(self):
        """ Action when the signal: 'Extent Changed' from QGIS MapCanvas is emitted&captured
         We connect a new signal: 'RenderComplete' to perform operation after the QGIS rendering (deferred strategy)

        """
        if self.bUseMutexAndBetaFunctionalities:
            # url: http://stackoverflow.com/questions/11261663/pyqt-qmutexlocker-not-released-on-exception
            with QMutexLocker(self.QMCanvasExtentsChanged):
                try:
                    QObject.connect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter*)"),
                                    self.canvasExtentsChangedAndRenderComplete)
                except:
                    qgis_log_tools.logMessageCRITICAL("Exception intercepted !")
        else:
            QObject.connect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter*)"),
                            self.canvasExtentsChangedAndRenderComplete)


    def canvasExtentsChangedAndRenderComplete(self):
        """ Action when the signal: 'Render Complete' from QGIS MapCanvas is emitted&captured (after a emitted&captured signal: 'Extent Changed') """
        #
        if self.bUseMutexAndBetaFunctionalities:
            with QMutexLocker(self.QMCanvasExtentsChangedAndRenderComplete):
                try:
                    QObject.disconnect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter*)"),
                                       self.canvasExtentsChangedAndRenderComplete)
                    #
                    self.update_track_position()
                except:
                    # import sys
                    #qgis_log_tools.logMessageCRITICAL("Exception intercepted : " + sys.exc_info()[0])
                    qgis_log_tools.logMessageCRITICAL("Exception intercepted : ")
        else:
            QObject.disconnect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter*)"),
                               self.canvasExtentsChangedAndRenderComplete)
            #
            self.update_track_position()

    def refreshComboBoxLayers(self):
        """ Action when the Combo Box attached to refreshing layers for tracking position is clicked """
        #
        qgis_log_tools.logMessageINFO("Launch 'refreshComboBoxLayers(...)' ...")
        self.dlg.trackingPositionLayerCombo.clear()
        layers = QgsMapLayerRegistry.instance().mapLayers().values()
        for layer in layers:
            # filter on layers to add in combobox
            if qgis_layer_tools.filter_layer_for_trackingposition(layer):
                self.dlg.trackingPositionLayerCombo.addItem(layer.name(), layer)
                if layer.name() == "camera_position":
                    self.idCameraPositionLayerInBox = self.dlg.trackingPositionLayerCombo.count() - 1
                    #
                    qgis_log_tools.logMessageINFO("camera_position layer found - id in combobox: " + str(
                        self.dlg.trackingPositionLayerCombo.currentIndex()))
        #
        self.dlg.trackingPositionLayerCombo.setCurrentIndex(self.idCameraPositionLayerInBox)

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

    def enabled_trackposition(self):
        """ Action when the checkbox 'Enable Tracking Position' is clicked """
        #
        qgis_log_tools.logMessageINFO("Launch 'enable_trackposition(...)' ...")

        if self.dlg.enableTrackPosition.isChecked():
            #
            self.refreshComboBoxLayers()
            #
            self.connectSignalForExtentsChanged()

            if self.bUseMutexAndBetaFunctionalities:
                self.cron_trackposition.start(self.cron_trackposition_delay)  # add a delay (con_trackposition_delay) in QTimer
        else:
            self.disconnectSignalForExtentsChanged()

            # if self.bUseMutexAndBetaFunctionalities:
            if self.cron_trackposition.isActive():
                self.cron_trackposition.stop()

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
        self.bUseMutexAndBetaFunctionalities = self.dlg.enableUseMutexForTP.isChecked()

        if self.dlg.enableUseMutexForTP.isChecked() and self.dlg.enableTrackPosition.isChecked():
            self.cron_trackposition.start(self.cron_trackposition_delay)  # add a delay (con_trackposition_delay) in QTimer
        else:
            if self.cron_trackposition.isActive():
                self.cron_trackposition.stop()

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
                if self.bUseMutexAndBetaFunctionalities:
                    self.cron_trackposition.start(self.cron_trackposition_delay)  # add a delay (con_trackposition_delay) in QTimer
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
                # if self.bUseMutexAndBetaFunctionalities:
                if self.cron_trackposition.isActive():
                    self.cron_trackposition.stop()

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

    def commitChangesAndRefresh(self):
        """ Perform a commitChanges on current layer and perform a refresh on QGIS MapCanvas """
        #
        resultCommit = qgis_layer_tools.commitChanges(self.currentLayer, self.iface, QSettings())
        #
        if resultCommit:
            qgis_mapcanvas_tools.refreshMapCanvas(self.iface)
        #
        return resultCommit

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
                    self.threshold = int(b)     # only use 'b' to change the threshold scale value
                except Exception:
                    validFormat = False     # problem with 'a'
            except Exception:
                validFormat = False     # problem with 'b'
        # Input format problem!
        if validFormat == False:
            qgis_log_tools.logMessageWARNING("Invalid input for scale! Scale format input : [int]:[int] or just [int]")

        # just for visualisation purpose
        self.dlg.threshold_extent.setText("1:" + str(self.threshold))

    # TODO: optimize update_track_position because it's a (critical) real-time method !
    def update_track_position(self, bWithProjectionInCRSLayer=True, bUseEmptyFields=False):
        """ Perform the update tracking position (in real-time)
        Save the current Qgis Extent (+metadatas) into a QGIS vector layer (compatible for tracking position).
        The QGIS Vector Layer need at least 2 attributes:
            - user_id: text
            - w_time: text

        :param bWithProjectionInCRSLayer: Option [default=True].
         If True, project the QGIS MapCanvas extent (QGIS World CRS) into Layer CRS

        :type bWithProjectionInCRSLayer: bool

        :param bUseEmptyFields: Option [default=False]
         If True, don't set the field (user_id, w_time)
         If False, use a autogenerate id for user (user name from OS + ip) and current date time (from QDateTime time stamp)
        :type bUseEmptyFields: bool

        """

        mapCanvas = self.iface.mapCanvas()

        # TODO: optimize this: not needed to check/test/find in realtime the layer (for tracking position)
        # # NEED TO OPTIMIZE ##
        # retrieve layer name from GUI (IMT)
        layerNameForTrackingPosition = self.dlg.trackingPositionLayerCombo.currentText()
        # search this layer
        layerPolygonExtent = qgis_mapcanvas_tools.find_layer_in_qgis_legend_interface(self.iface, layerNameForTrackingPosition)
        if layerPolygonExtent is None:
            qgis_log_tools.logMessageWARNING("No layer found for tracking position")
            return 0
        ## NEED TO OPTIMIZE ##

        mapcanvas_extent = mapCanvas.extent()

        # if max(mapcanvas_extent.width(), mapcanvas_extent.height()) > threshold:
        if mapCanvas.scale() > self.threshold:
            qgis_log_tools.logMessageWARNING("MapCanvas extent scale exceed the Threshold scale for tracking")
            qgis_log_tools.logMessageWARNING(
                "-> MapCanvas scale= " + str(mapCanvas.scale()) +
                "\tThreshold scale= " + str(self.threshold))
            return -2

        #
        list_points_from_mapcanvas = imt_tools.construct_listpoints_from_extent(mapcanvas_extent)

        ## NEED TO OPTIMIZE ##
        if bWithProjectionInCRSLayer:
            # url: http://qgis.org/api/classQgsMapCanvas.html#af0ffae7b5e5ec8b29764773fa6a74d58
            extent_src_crs = mapCanvas.mapSettings().destinationCrs()
            # url: http://qgis.org/api/classQgsMapLayer.html#a40b79e2d6043f8ec316a28cb17febd6c
            extent_dst_crs = layerPolygonExtent.crs()
            # url: http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/crs.html
            xform = QgsCoordinateTransform(extent_src_crs, extent_dst_crs)
            #
            try:
                list_points = [xform.transform(point) for point in list_points_from_mapcanvas]
            except QgsCsException as e:
                qgis_log_tools.logMessageCRITICAL("QgsCsException => " + str(e))
        else:
            list_points = list_points_from_mapcanvas
        ## NEED TO OPTIMIZE ##

        gPolygon = QgsGeometry.fromPolygon([list_points])

        fet = QgsFeature()

        fet.setGeometry(gPolygon)

        # set Attributes for Layer in DB
        # On récupère automatiquement le nombre de champs qui compose les features présentes dans ce layer
        # How to get field names in pyqgis 2.0
        # url: http://gis.stackexchange.com/questions/76364/how-to-get-field-names-in-pyqgis-2-0
        dataProvider = layerPolygonExtent.dataProvider()

        # Return a map of indexes with field names for this layer.
        # url: http://qgis.org/api/classQgsVectorDataProvider.html#a53f4e62cb05889ecf9897fc6a015c296
        fields = dataProvider.fields()

        if bUseEmptyFields:
            # how to fill a list with 0 using python
            # url: http://stackoverflow.com/questions/5908420/how-to-fill-a-list-with-0-using-python
            #from itertools import repeat
            #values = list(repeat(None, fields.count()))
            values = [None for i in range(fields.count())]
        else:
            ## NEED TO OPTIMIZE ##
            # get fields name from the layer
            field_names = [field.name() for field in fields]

            # find index for field 'user-id'
            id_user_id_field = imt_tools.find_index_field_by_name(field_names, "user_id")
            if id_user_id_field == -1:
                qgis_log_tools.logMessageWARNING(
                    "No \"user_id\"::text field attributes found in layer: " + layerPolygonExtent.name())
                return -1

            # find index for field 'writing_time'
            id_w_time_field = imt_tools.find_index_field_by_name(field_names, "w_time")
            if id_w_time_field == -1:
                qgis_log_tools.logMessageWARNING(
                    "No \"w_time\"::text attributes found in layer: " + layerPolygonExtent.name())
                return -1
            ## NEED TO OPTIMIZE ##

            # # Retrieve informations
            # static information (for a session)
            user_name = self.trackposition_user_name

            # get the current time in a Qt string format
            timestamp_string = imt_tools.get_timestamp_from_qt_string_format()

            # set the fields
            # reset all fields in None
            values = [None for i in range(fields.count())]
            # set some fields (user_id, time)
            values[id_user_id_field] = user_name
            values[id_w_time_field] = timestamp_string

        fet.setAttributes(values)

        # How can I programatically create and add features to a memory layer in QGIS 1.9?
        # url: http://gis.stackexchange.com/questions/60473/how-can-i-programatically-create-and-add-features-to-a-memory-layer-in-qgis-1-9
        # write the layer and send request to DB
        layerPolygonExtent.startEditing()
        layerPolygonExtent.addFeatures([fet], True)

        ## NEED TO OPTIMIZE ##
        #
        # layerPolygonExtent.updateFields()
        # layerPolygonExtent.updateExtents()
        ## NEED TO OPTIMIZE ##

        if self.bUseMutexAndBetaFunctionalities:
            #self.trackposition_queue.put(layerPolygonExtent)
            # with self.trackposition_queue.mutex:
            self.trackposition_queue.put(layerPolygonExtent.name())
            resultCommit = True
        else:
            #
            resultCommit = layerPolygonExtent.commitChanges()
            #
            if resultCommit:
                qgis_log_tools.logMessageINFO("Location saved in layer: " + layerPolygonExtent.name())
            else:
                qgis_log_tools.logMessageCRITICAL(
                    "saving position failed : are you sure the selected tracking layer: " + layerPolygonExtent.name() +
                    "has at least 2 attributes : \"user_id\"::text and \"w_time\"::text")

                commitErrorString = layerPolygonExtent.commitErrors()[2]
                commitErrorStringShort = commitErrorString[commitErrorString.rfind(":") + 2:len(
                    commitErrorString)]  # +2 to skip ': ' prefix of commitError msg
                self.iface.messageBar().pushMessage("IMT. ERROR : " + "\"" + commitErrorStringShort + "\"",
                                                    "",
                                                    QgsMessageBar.CRITICAL, 0)
        #
        return resultCommit

    def cronTrackPositionEvent(self):
        """ [BETA] Action perform when the QTimer for Tracking Position is time out
        Try to enqueue request from Tracking Position to amortize the cost&effect on QGIS GUI

        """

        qgis_log_tools.logMessage("launch conTrackPositionEvent(...)")

        #
        # with self.trackposition_queue.mutex:
        if not self.trackposition_queue.empty():

            layer_name_to_commit = str(self.trackposition_queue.get())
            qgis_log_tools.logMessage("consume a commitChanges request for this layer: " + layer_name_to_commit)

            #layer_to_commit = qgis_mapcanvas_tools.find_layer_in_mapcanvas(self.iface.mapCanvas(), layer_name_to_commit)
            layer_to_commit = qgis_mapcanvas_tools.find_layer_in_qgis_legend_interface(self.iface, layer_name_to_commit)
            if layer_to_commit is None:
                qgis_log_tools.logMessageWARNING("No layer found for tracking position")
                return 0

            resultCommit = layer_to_commit.commitChanges()

            #
            if resultCommit == True:
                qgis_log_tools.logMessageINFO("Location saved in layer: " + layer_to_commit.name())
                # TODO: clear the queue (modify/optimize this 'dummy' strategy)
                while not self.trackposition_queue.empty():
                    self.trackposition_queue.get()  # as docs say: Remove and return an item from the queue.
            else:
                qgis_log_tools.logMessageCRITICAL(
                    "saving position failed : are you sure the selected tracking layer: " + layer_to_commit.name() +
                    "has at least 2 attributes : \"user_id\"::text and \"w_time\"::text")
                # get the last element of the list
                # url: http://stackoverflow.com/questions/930397/getting-the-last-element-of-a-list-in-python
                commitErrorString = layer_to_commit.commitErrors()[-1]
                # format the string error
                commitErrorStringShort = commitErrorString[commitErrorString.rfind(":") + 2:len(
                    commitErrorString)]  # +2 to skip ': ' prefix of commitError msg
                self.iface.messageBar().pushMessage("IMT. ERROR : " + "\"" + commitErrorStringShort + "\"",
                                                    "",
                                                    QgsMessageBar.CRITICAL, 0)
