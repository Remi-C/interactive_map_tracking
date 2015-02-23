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

from collections import namedtuple

import time

# import logging
#
# # logging.shutdown()
# reload(logging)
#
# class QGISHandler(logging.Handler):
# def emit(self, record):
#         msg = self.format(record)
#         QgsMessageLog.logMessage(msg)


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

        # self.idCameraPositionLayerInBox = 0
        self.currentLayerForTrackingPosition = None

        self.bSignalForProjectReadConnected = True
        QObject.connect(self.iface, SIGNAL("projectRead()"), self.qgisInterfaceProjectRead)

        # MUTEX
        self.bUseMutexAndBetaFunctionalities = self.dlg.enableUseMutexForTP.isChecked()
        self.QMCanvasExtentsChanged = QMutex()
        self.QMCanvasExtentsChangedAndRenderComplete = QMutex()


        #url: https://docs.python.org/2/library/collections.html#collections.namedtuple
        # Definition : namedtuples 'type'
        self.TP_NAMEDTUPLE_LET = namedtuple('TP_NAMEDTUPLE_LET', ['layer', 'extent', 'w_time'])
        self.TP_NAMEDTUPLE_ET = namedtuple('TP_NAMEDTUPLE_ET', ['extent', 'w_time'])
        # LIFO Queue to save (in real time) requests for tracking position
        self.tp_queue_rt_ntuples_let = Queue.LifoQueue()
        self.tp_queue_mutex = QMutex()
        self.tp_rt_ntuples_let = {}
        self.tp_dict_mutex_let = QMutex()
        self.tp_dict_key_l_values_et = {}
        self.tp_list_fets_mutex = QMutex()
        self.tp_list_fets = []
        self.tp_dict_mutex_llf = QMutex()
        self.tp_dict_key_l_values_listfeatures = {}
        self.tp_list_mutex_ltc = QMutex()
        self.tp_list_layers_to_commit = []
        #
        self.qtimer_tracking_position_rtt_to_memory = QTimer()
        self.qtimer_tracking_position_rtt_to_memory.timeout.connect(self.tracking_position_rtt_to_memory)
        self.qtimer_tracking_position_memory_to_geom = QTimer()
        self.qtimer_tracking_position_memory_to_geom.timeout.connect(self.tracking_position_memory_to_geom)
        self.qtimer_tracking_position_geom_to_layer = QTimer()
        self.qtimer_tracking_position_geom_to_layer.timeout.connect(self.tracking_position_geom_to_layer)
        self.qtimer_tracking_position_layers_to_commit = QTimer()
        self.qtimer_tracking_position_layers_to_commit.timeout.connect(self.tracking_position_layers_to_commit)
        # OPTIONS: timing reactions
        # TODO : think about time and chaining condition
        self.tp_threshold_time_for_realtime_tracking_position = 0.125     # i.e. 8hz => (max) 8 tracking positions record per second
        self.tp_threshold_time_for_tp_to_mem = 0.125                # add to reference timing: realtime_tracking_position
        self.tp_threshold_time_for_construct_geom = 5.00            # add to reference timing: tp_to_mem
        self.tp_threshold_time_for_sending_geom_to_layer = 0.250    # add to reference timing: construct_geom
        self.tp_threshold_time_for_sending_layer_to_dp = 0.500      # add to reference timing: sending_geom_to_layer
        #
        self.delta_time_still_moving = 0.750    # delta time used to decide if the user still moving on the map
        # for timing
        import time
        current_time = time.time()
        self.tp_time_last_tp_to_mem = current_time - self.tp_threshold_time_for_realtime_tracking_position - self.tp_threshold_time_for_tp_to_mem
        self.tp_time_last_construct_geom = self.tp_time_last_tp_to_mem - self.tp_threshold_time_for_construct_geom
        self.tp_time_last_send_geom_to_layer = self.tp_time_last_construct_geom - self.tp_threshold_time_for_sending_geom_to_layer
        self.tp_time_last_send_layer_to_dp = self.tp_time_last_send_geom_to_layer - self.tp_threshold_time_for_sending_layer_to_dp
        """
        Delay on manager of trackposition requests
        can be interesting to evaluate/benchmark the impact on this value
        """
        # self.qtimer_tracking_position_delay = 5000  # in ms
        self.qtimer_tracking_position_delay = 10  # in ms
        #self.qtimer_tracking_position_delay = 500   # in ms

        # user-id:
        # from user id OS
        os_username = imt_tools.get_os_username()
        # try to use IP to identify the user
        user_ip = imt_tools.get_lan_ip()
        #
        self.tp_user_name = os_username + " (" + user_ip + ")"

        qgis_logger = qgis_log_tools.QGISLogger()
        qgis_logger.log("test1")
        qgis_logger.log("test2")

        self.tp_id_user_id = 0
        self.tp_id_w_time = 0
        self.values = []

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
        # box for tracking layers
        self.dlg.refreshLayersListForTrackPosition.clicked.connect(self.refreshComboBoxLayers)
        QObject.connect(self.dlg.trackingPositionLayerCombo, SIGNAL("currentIndexChanged ( const QString & )"),
                        self.currentIndexChangedTPLCB)

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
            self.dlg.threshold_extent.setText("200")
            self.dlg.threshold_extent.setDisabled(True)

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
            # with QMutexLocker(self.QMCanvasExtentsChangedAndRenderComplete):
            #     try:
            #         QObject.disconnect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter*)"),
            #                            self.canvasExtentsChangedAndRenderComplete)
            #         #
            #         self.update_track_position()
            #     except:
            #         # import sys
            #         #qgis_log_tools.logMessageCRITICAL("Exception intercepted : " + sys.exc_info()[0])
            #         qgis_log_tools.logMessageCRITICAL("Exception intercepted : ")
            QObject.disconnect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter*)"),
                               self.canvasExtentsChangedAndRenderComplete)
            #
            self.update_track_position()
        else:
            QObject.disconnect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter*)"),
                               self.canvasExtentsChangedAndRenderComplete)
            #
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
        idComboBoxIndexForCameraPosition = -1

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
                if layer.name() == "camera_position":
                    idComboBoxIndexForCameraPosition = idComboBoxIndex
                    #
                    qgis_log_tools.logMessageINFO("camera_position layer found - id in combobox: " + str(
                        idComboBoxIndexForCameraPosition))

        # update GUI
        if idComboBoxIndexForCameraPosition != -1:
            self.dlg.trackingPositionLayerCombo.setCurrentIndex(idComboBoxIndexForCameraPosition)
            idComboBoxIndex = idComboBoxIndexForCameraPosition

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
                # add a delay (con_trackposition_delay) in QTimer
                self.qtimer_tracking_position_rtt_to_memory.start(self.qtimer_tracking_position_delay)
                self.qtimer_tracking_position_memory_to_geom.start(self.qtimer_tracking_position_delay)
                self.qtimer_tracking_position_geom_to_layer.start(self.qtimer_tracking_position_delay)
                self.qtimer_tracking_position_layers_to_commit.start(self.qtimer_tracking_position_delay)
        else:
            self.disconnectSignalForExtentsChanged()

            if self.qtimer_tracking_position_rtt_to_memory.isActive():
                self.qtimer_tracking_position_rtt_to_memory.stop()
            if self.qtimer_tracking_position_memory_to_geom.isActive():
                self.qtimer_tracking_position_memory_to_geom.stop()
            if self.qtimer_tracking_position_geom_to_layer.isActive():
                self.qtimer_tracking_position_geom_to_layer.stop()
            if self.qtimer_tracking_position_layers_to_commit.isActive():
                self.qtimer_tracking_position_layers_to_commit.stop()

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
            # add a delay (con_trackposition_delay) in QTimer
            self.qtimer_tracking_position_rtt_to_memory.start(self.qtimer_tracking_position_delay)
            self.qtimer_tracking_position_memory_to_geom.start(self.qtimer_tracking_position_delay)
            self.qtimer_tracking_position_geom_to_layer.start(self.qtimer_tracking_position_delay)
            self.qtimer_tracking_position_layers_to_commit.start(self.qtimer_tracking_position_delay)
        else:
            if self.qtimer_tracking_position_rtt_to_memory.isActive():
                self.qtimer_tracking_position_rtt_to_memory.stop()
            if self.qtimer_tracking_position_memory_to_geom.isActive():
                self.qtimer_tracking_position_memory_to_geom.stop()
            if self.qtimer_tracking_position_geom_to_layer.isActive():
                self.qtimer_tracking_position_geom_to_layer.stop()
            if self.qtimer_tracking_position_layers_to_commit.isActive():
                self.qtimer_tracking_position_layers_to_commit.stop()

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
                    # add a delay (con_trackposition_delay) in QTimer
                    self.qtimer_tracking_position_rtt_to_memory.start(self.qtimer_tracking_position_delay)
                    self.qtimer_tracking_position_memory_to_geom.start(self.qtimer_tracking_position_delay)
                    self.qtimer_tracking_position_geom_to_layer.start(self.qtimer_tracking_position_delay)
                    self.qtimer_tracking_position_layers_to_commit.start(self.qtimer_tracking_position_delay)
        else:
            self.dlg.enableAutoSave.setDisabled(True)
            self.dlg.enableTrackPosition.setDisabled(True)
            self.dlg.enableLogging.setDisabled(True)
            self.dlg.thresholdLabel.setDisabled(True)
            self.dlg.threshold_extent.setDisabled(True)
            self.dlg.enableUseMutexForTP.setDisabled(True)
            #
            self.disconnectSignalForLayerChanged()
            if self.dlg.enableAutoSave.isChecked():
                self.disconnectSignalForLayerModified(self.currentLayer)
            if self.dlg.enableTrackPosition.isChecked():
                self.disconnectSignalForExtentsChanged()

                if self.qtimer_tracking_position_rtt_to_memory.isActive():
                    self.qtimer_tracking_position_rtt_to_memory.stop()
                if self.qtimer_tracking_position_memory_to_geom.isActive():
                    self.qtimer_tracking_position_memory_to_geom.stop()
                if self.qtimer_tracking_position_geom_to_layer.isActive():
                    self.qtimer_tracking_position_geom_to_layer.stop()
                if self.qtimer_tracking_position_layers_to_commit.isActive():
                    self.qtimer_tracking_position_layers_to_commit.stop()

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

        if self.bUseMutexAndBetaFunctionalities:
            #
            rt_ntuple = self.TP_NAMEDTUPLE_LET(
                    layer_for_polygon_extent,
                    mapcanvas_extent,
                    # imt_tools.get_timestamp_from_qt_string_format()
                    imt_tools.get_timestamp()
            )
            #
            if self.tp_rt_ntuples_let == {}:
                self.tp_rt_ntuples_let = rt_ntuple
                qgis_log_tools.logMessageINFO("New tracking position")
            else:
                tp_delta_time_rt = rt_ntuple.w_time - self.tp_rt_ntuples_let.w_time
                if tp_delta_time_rt >= self.tp_threshold_time_for_realtime_tracking_position:
                    self.tp_rt_ntuples_let = rt_ntuple
                    #
                    with QMutexLocker(self.tp_queue_mutex):
                        self.tp_queue_rt_ntuples_let.put(rt_ntuple)
                    #
                    qgis_log_tools.logMessageINFO("New tracking position - elapsed time: " + str(tp_delta_time_rt))

            resultCommit = True


        else:


             # filter on extent size
            try:
                threshold = int(self.dlg.threshold_extent.text())
            except Exception:
                qgis_log_tools.logMessageWARNING("Threshold can only be a number")
                return -1

            if max(mapcanvas_extent.width(), mapcanvas_extent.height()) > threshold:
                qgis_log_tools.logMessageWARNING("MapCanvas extent size exceed the Threshold size for tracking")
                qgis_log_tools.logMessageWARNING(
                    "-> MapCanvas extent size= " + str(max(mapcanvas_extent.width(), mapcanvas_extent.height())) +
                    "\tThreshold size= " + str(threshold))
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


    def tracking_position_rtt_to_memory(self):
        """ [BETA] Action perform when the QTimer for Tracking Position is time out
        Try to enqueue request from Tracking Position to amortize the cost&effect on QGIS GUI

        """
        if self.tp_rt_ntuples_let == {}:
            return
        current_time = time.time()
        delta_time_mem = current_time - self.tp_time_last_tp_to_mem
        # qgis_log_tools.logMessageINFO("delta_time_mem: " + str(delta_time_mem))
        # if delta_time_mem >= self.tp_threshold_time_for_tp_to_mem:
        if True:
            # qgis_log_tools.QGISLogger().log("qtimer_tracking_position_event(...)")
            #qgis_log_tools.logMessage("qtimer_tracking_position_event(...)")

            # Lock the mutex on Tracking Position queue
            # because this queue is used on real tim tracking (with signal/event from QGIS GUI)
            # so we can't be sure that this queue will not be modified when we will use it (in this "thread")
            with QMutexLocker(self.tp_queue_mutex):
                #qgis_log_tools.logMessage("size of tq_queue_namedtuple :" + str(self.tp_queue_rt_ntuples_let.qsize()))
                with QMutexLocker(self.tp_dict_mutex_let):
                    while not self.tp_queue_rt_ntuples_let.empty():
                        tp_tuple = self.tp_queue_rt_ntuples_let.get()
                        # url: http://stackoverflow.com/questions/20585920/how-to-add-multiple-values-to-a-dictionary-key-in-python
                        self.tp_dict_key_l_values_et.setdefault(tp_tuple.layer, []).append(
                            self.TP_NAMEDTUPLE_ET(tp_tuple.extent, tp_tuple.w_time)
                        )
                        qgis_log_tools.logMessageINFO("append tuples")

                        # update timer
                        current_time = time.time()
                        self.tp_time_last_tp_to_mem = current_time
                # release the mutex on: tp_dict_key_l_values_et
            # release the mutex: tp_queue_mutex

    def tracking_position_memory_to_geom(self):
        """

        :return:

        """
        current_time = time.time()
        delta_time_construct_geom = (current_time - self.tp_time_last_tp_to_mem) + (self.tp_time_last_tp_to_mem - self.tp_time_last_construct_geom)
        # qgis_log_tools.logMessageINFO("delta_time_construct_geom: " + str(delta_time_construct_geom))

        if delta_time_construct_geom >= self.tp_threshold_time_for_construct_geom:
            with QMutexLocker(self.tp_dict_mutex_let):
                ## NEED TO OPTIMIZE ##
                try:
                    threshold = int(self.dlg.threshold_extent.text())
                except Exception:
                    qgis_log_tools.logMessageWARNING("Threshold can only be a number")
                    return -1
                ## NEED TO OPTIMIZE ##

                mapCanvas = self.iface.mapCanvas()

                # url: http://qgis.org/api/classQgsMapCanvas.html#af0ffae7b5e5ec8b29764773fa6a74d58
                extent_src_crs = mapCanvas.mapSettings().destinationCrs()

                for layer in self.tp_dict_key_l_values_et.keys():
                    layer_to_commit = layer

                    # url: http://qgis.org/api/classQgsMapLayer.html#a40b79e2d6043f8ec316a28cb17febd6c
                    extent_dst_crs = layer_to_commit.crs()
                    # url: http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/crs.html
                    xform = QgsCoordinateTransform(extent_src_crs, extent_dst_crs)

                    tp_list_fets = []

                    # pop key from tracking position dictionary
                    list_ntuples = self.tp_dict_key_l_values_et.pop(layer)
                    for tp_namedtuple in list_ntuples:
                        #qgis_log_tools.logMessage("consume a request track_position in queue ...")

                        mapcanvas_extent = tp_namedtuple.extent
                        w_time = tp_namedtuple.w_time

                        # filter on extent size
                        if max(mapcanvas_extent.width(), mapcanvas_extent.height()) > threshold:
                            qgis_log_tools.logMessageWARNING("MapCanvas extent size exceed the Threshold size for tracking")
                            qgis_log_tools.logMessageWARNING(
                                "MapCanvas extent size= " + str(max(mapcanvas_extent.width(), mapcanvas_extent.height())) +
                                "\tThreshold size= " + str(threshold))
                            return -2

                        # get the list points from the current extent (from QGIS MapCanvas)
                        list_points_from_mapcanvas = imt_tools.construct_listpoints_from_extent(mapcanvas_extent)

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

                        with QMutexLocker(self.tp_list_mutex_ltc):
                            qgis_log_tools.logMessageINFO("append features")

                            tp_list_fets.append(fet)

                            # update timer
                            current_time = time.time()
                            self.tp_time_last_construct_geom = current_time

                    qgis_log_tools.logMessage("size of tp_list_fets :" + str(len(tp_list_fets)))

                    with QMutexLocker(self.tp_dict_mutex_llf):
                        self.tp_dict_key_l_values_listfeatures.setdefault(layer, []).append(tp_list_fets)

    def tracking_position_geom_to_layer(self):
        """

        :return:

        """
        current_time = time.time()
        #delta_time_send_geom_to_layer = current_time - self.tp_time_last_send_geom_to_layer
        # delta_time_send_geom_to_layer = self.tp_time_last_construct_geom - self.tp_time_last_send_geom_to_layer
        delta_time_send_geom_to_layer = (current_time - self.tp_time_last_construct_geom) + (self.tp_time_last_construct_geom - self.tp_time_last_send_layer_to_dp)
        # qgis_log_tools.logMessageINFO("delta_time_send_geom_to_layer: " + str(current_time - self.tp_time_last_construct_geom))
        b_still_moving = (current_time - self.tp_time_last_construct_geom) <= self.delta_time_still_moving
        if delta_time_send_geom_to_layer >= self.tp_threshold_time_for_sending_geom_to_layer \
                and not b_still_moving:

            with QMutexLocker(self.tp_dict_mutex_llf):
                for layer in self.tp_dict_key_l_values_listfeatures.keys():
                    qgis_log_tools.logMessageINFO("Send Geometries to layer (start edit)")

                    # from the dict we retrieve a list of list
                    tp_list_of_list_fets = self.tp_dict_key_l_values_listfeatures.pop(layer)

                    qgis_log_tools.logMessageINFO("len(tp_list_of_list_fets): " + str(len(tp_list_of_list_fets)))
                    #
                    # How can I programatically create and add features to a memory layer in QGIS 1.9?
                    # url: http://gis.stackexchange.com/questions/60473/how-can-i-programatically-create-and-add-features-to-a-memory-layer-in-qgis-1-9
                    # write the layer and send request to DB
                    layer.startEditing()
                    for tp_list_fets in tp_list_of_list_fets:
                        layer.addFeatures(tp_list_fets, False)  # bool_makeSelected=False

                    with QMutexLocker(self.tp_list_mutex_ltc):
                        self.tp_list_layers_to_commit.append(layer)
                        qgis_log_tools.logMessageINFO("append to layers_to_commit")

                        # update timer
                        current_time = time.time()
                        self.tp_time_last_send_geom_to_layer = current_time

    def tracking_position_layers_to_commit(self):
        """

        :return:

        """
        current_time = time.time()
        delta_time_send_layer_to_dp = (current_time - self.tp_time_last_send_geom_to_layer) + (self.tp_time_last_send_geom_to_layer - self.tp_time_last_send_layer_to_dp)
        # delta_time_send_layer_to_dp = current_time - self.tp_time_last_send_geom_to_layer
        # qgis_log_tools.logMessageINFO("delta_time_send_layer_to_dp: " + str(delta_time_send_layer_to_dp) + "\tself.tp_threshold_time_for_sending_layer_to_dp: " + str(self.tp_threshold_time_for_sending_layer_to_dp))
        # qgis_log_tools.logMessageINFO("self.tp_time_last_send_layer_to_dp: " + str(self.tp_time_last_send_layer_to_dp))
        # qgis_log_tools.logMessageINFO("self.tp_time_last_send_geom_to_layer: " + str(self.tp_time_last_send_geom_to_layer))

        bTimeToCommit = delta_time_send_layer_to_dp > self.tp_threshold_time_for_sending_layer_to_dp

        if bTimeToCommit:
            with QMutexLocker(self.tp_list_mutex_ltc):
                while self.tp_list_layers_to_commit != []:
                    qgis_log_tools.logMessageINFO("Send Layer (changed) to DataProvider (commitChanges)")
                    layer_to_commit = self.tp_list_layers_to_commit.pop()
                    #
                    try:
                        resultCommit = layer_to_commit.commitChanges()
                        qgis_log_tools.logMessageINFO("commit change layer")

                        current_time = time.time()
                        self.tp_time_last_send_layer_to_dp = current_time
                    except:
                        pass
