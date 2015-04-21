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
# Initialize Qt resources from file resources.py
# Import the code for the dialog
import os.path
from qgis.gui import QgsMessageBar
from qgis.core import *

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtCore import QUrl, QReadWriteLock, QReadLocker, pyqtSlot
from PyQt4.QtGui import QAction, QIcon, QTabWidget
from PyQt4.QtWebKit import QWebSettings

from interactive_map_tracking_dialog import interactive_map_trackingDialog
import qgis_layer_tools
import qgis_log_tools
import imt_tools
from signalsmanager import SignalsManager
from autosave import AutoSave
from trafipollu import TrafiPollu
from decorators import DecoratorsForQt


#
# for beta test purposes
#
from PyQt4.QtCore import QTimer
import Queue
import time
from PyQt4.QtNetwork import QNetworkProxy

from collections import namedtuple


def CONVERT_S_TO_MS(s):
    return s * 1000


class interactive_map_tracking:
    """QGIS Plugin Implementation."""

    qsettings_group_name = "IMT"

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        current_time = time.time()

        # Clean QSettings
        self.qsettings = QSettings()

        # self.clean_qsettings()
        # imt_tools.print_group_name_values_in_qsettings(self.qsettings_group_name)

        self.currentLayer = None

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.qgis_plugins_directory = os.path.normcase(os.path.dirname(__file__))
        # initialize locale
        locale = self.qsettings.value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.qgis_plugins_directory,
            'i18n',
            'interactive_map_tracking_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        # print "declare dlg here !"
        # if not 'dlg' in dir(self):
        self.dlg = interactive_map_trackingDialog()
        # print "- self.dlg: ", self.dlg

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Interactive Map Tracking')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'interactive_map_tracking')
        self.toolbar.setObjectName(u'interactive_map_tracking')

        self.signals_manager = SignalsManager.instance()
        self.autosave = AutoSave(self.iface, self.dlg.enableAutoSave)
        self.tp_layer = None

        self.trafipollu = TrafiPollu(self.iface, self.dlg)

        # MUTEX
        self.b_use_asynch = self.dlg.enableUseMutexForTP.isChecked()

        # url: https://docs.python.org/2/library/collections.html#collections.namedtuple
        # Definition : namedtuples 'type'
        self.TP_NAMEDTUPLE_LET = namedtuple('TP_NAMEDTUPLE_LET', ['id_layer', 'extent', 'w_time'])
        self.TP_NAMEDTUPLE_ET = namedtuple('TP_NAMEDTUPLE_ET', ['extent', 'w_time'])
        # LIFO Queue to save (in real time) requests for tracking position
        self.tp_queue_rt_ntuples_let = Queue.LifoQueue()
        self.tp_dict_key_l_values_et = {}
        self.tp_list_fets = []
        self.tp_dict_key_l_values_listfeatures = {}
        self.tp_dict_layers_to_commit = {}
        #
        self.qtimer_tracking_position_rtt_to_memory = QTimer()
        self.qtimer_tracking_position_memory_to_geom = QTimer()
        self.qtimer_tracking_position_geom_to_layer = QTimer()
        self.qtimer_tracking_position_layers_to_commit = QTimer()
        #
        self.signals_manager.add_timeout(self.qtimer_tracking_position_rtt_to_memory,
                                         self.slot_tp_rttp_to_memory,
                                         "QTIMER")
        self.signals_manager.add_timeout(self.qtimer_tracking_position_memory_to_geom,
                                         self.slot_memory_to_geom_tp,
                                         "QTIMER")
        self.signals_manager.add_timeout(self.qtimer_tracking_position_geom_to_layer,
                                         self.slot_geom_to_layer_tp,
                                         "QTIMER")
        self.signals_manager.add_timeout(self.qtimer_tracking_position_layers_to_commit,
                                         self.slot_layers_to_commit_tp,
                                         "QTIMER")

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
        self.threshold = 0

        self.tp_id_user_id = 0
        self.tp_id_w_time = 0
        self.values = []

        self.bRefreshMapFromAutoSave = False

        self.TP_NAMEDTUPLE_WEBVIEW = namedtuple(
            'TP_NAMEDTUPLE_WEBVIEW',
            ['state', 'width', 'height', 'online_url', 'offline_url']
        )
        # very dirty @FIXME @TODO : here is the proper way to do it (from within the class `self.plugin_dir`)
        self.webview_offline_about = os.path.join(self.qgis_plugins_directory, "gui_doc", "About.htm")
        self.webview_offline_user_doc = os.path.join(self.qgis_plugins_directory, "gui_doc",
                                                     "Simplified_User_Guide.htm")
        self.webview_online_about = "https://github.com/Remi-C/interactive_map_tracking/wiki/[User]-About"
        self.webview_online_user_doc = "https://github.com/Remi-C/interactive_map_tracking/wiki/[User]-User-Guide"
        #
        self.webview_online_itown = "http://www.itowns.fr/api/testAPI.html"

        self.webview_dict = {}
        # url : http://qt-project.org/doc/qt-4.8/qurl.html
        self.webview_default_tuple = self.TP_NAMEDTUPLE_WEBVIEW('init', 0, 0, QUrl(""), QUrl(""))
        self.webview_dict[self.dlg.webView_userdoc] = self.TP_NAMEDTUPLE_WEBVIEW(
            'init',
            0, 0,
            QUrl(self.webview_online_user_doc),
            QUrl(self.webview_offline_user_doc)
        )
        self.webview_dict[self.dlg.webView_about] = self.TP_NAMEDTUPLE_WEBVIEW(
            'init',
            0, 0,
            QUrl(self.webview_online_about),
            QUrl(self.webview_offline_about)
        )
        self.webview_current = None
        self.webview_margin = 60
        self.webview_tab_index = -1

        # getting proxy
        self._set_proxy_()

        self.dict_tabs_size = {}  # dict useful for using setdefault(...)

        self.tp_last_extent_saved = QgsRectangle()

        # LOCKER for protecting layers (ptr) from QGIS
        # used by our asynchronous tracking method
        # -> to ensure protection when/if user want to delete the tracking layer
        self.tp_mutex_on_layers = QReadWriteLock()

        self.qgsmap_layer_registry = QgsMapLayerRegistry.instance()
        #
        self.mapCanvas = self.iface.mapCanvas()

        from qgis.core import QgsProject
        self.connect_signal_qgis(QgsProject.instance(), "readProject(const QDomDocument & )", self.slot_readProject)

        # self.list_id_checkbox = [
        # 'enablePlugin',
        #     'enableAutoSave',
        #     'enableTrackPosition',
        #     'enableLogging',
        #     'enableUseMutexForTP'
        # ]
        # print "imt_tools.build_list_member_name_qt_checkbox: ", imt_tools.build_list_member_name_qt_checkbox(self.dlg)
        self.list_id_checkbox = imt_tools.build_list_member_name_filter_qcheckbox(self.dlg)

    def slot_readProject(self):
        """

        :return:
        """
        self.enabled_pluging()

    def clean_qsettings(self):
        """

        :return:
        """
        print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        print "CLEAN QSETTINGS !!! DON'T FORGET TO REMOVE !!!"
        print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        #
        self.qsettings.beginGroup("interactive_map_tracking_plugin")
        self.qsettings.remove("")
        self.qsettings.endGroup()
        self.qsettings.beginGroup(self.qsettings_group_name)
        self.qsettings.remove("")
        self.qsettings.endGroup()

    def get_dlg(self):
        """
        For decorator
        :return:
        """
        return self.dlg

    def _set_proxy_(self):
        """

        :return:
        """
        s = self.qsettings  # getting proxy from qgis options settings
        proxyEnabled = s.value("proxy/proxyEnabled", "")
        proxyType = s.value("proxy/proxyType", "")
        proxyHost = s.value("proxy/proxyHost", "")
        proxyPort = s.value("proxy/proxyPort", "")
        proxyUser = s.value("proxy/proxyUser", "")
        proxyPassword = s.value("proxy/proxyPassword", "")
        if proxyEnabled == "true":  # test if there are proxy settings
            proxy = QNetworkProxy()
            if proxyType == "DefaultProxy":
                proxy.setType(QNetworkProxy.DefaultProxy)
            elif proxyType == "Socks5Proxy":
                proxy.setType(QNetworkProxy.Socks5Proxy)
            elif proxyType == "HttpProxy":
                proxy.setType(QNetworkProxy.HttpProxy)
            elif proxyType == "HttpCachingProxy":
                proxy.setType(QNetworkProxy.HttpCachingProxy)
            elif proxyType == "FtpCachingProxy":
                proxy.setType(QNetworkProxy.FtpCachingProxy)
            proxy.setHostName(proxyHost)
            proxy.setPort(int(proxyPort))
            proxy.setUser(proxyUser)
            proxy.setPassword(proxyPassword)
            QNetworkProxy.setApplicationProxy(proxy)

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

        # icon_path = ':/plugins/interactive_map_tracking/icon.png'
        icon_path = self.qgis_plugins_directory + '/icon.png'   # TODO: problem with Qt ressources
        # icon_path = ':/plugins/interactive_map_tracking/icon_svg.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Tools for Interactive Map Tracking'),
            callback=self.run,
            parent=self.iface.mainWindow())

        #
        self.init_signals()
        self.init_plugin()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        # print "unload"
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&Interactive Map Tracking'), action)
            self.iface.removeToolBarIcon(action)
        #
        self.signals_manager.disconnect_all()
        # TODO: use a manager for mutex too !
        # can be useful at the end (QGIS closes), to avoid dead-lock
        self.tp_mutex_on_layers.unlock()
        #
        self.autosave.disable()
        self.trafipollu.disable()

    def onResizeEvent(self, event):
        # url: http://openclassrooms.com/forum/sujet/dimensionnement-automatique-d-une-qtabwidget
        QTabWidget.resizeEvent(self.dlg.IMT_Window_Tabs, event)
        # url: http://qt-project.org/doc/qt-4.8/qresizeevent.html
        self.dict_tabs_size[self.dlg.IMT_Window_Tabs.currentIndex()] = event.size()

    def run(self):
        """Run method that performs all the real work"""
        #
        # set the icon IMT ^^
        # icon_path = ':/plugins/interactive_map_tracking/icon.png'
        icon_path = self.qgis_plugins_directory + '/icon.png'
        qgis_log_tools.logMessageINFO(str(self.qgis_plugins_directory + 'icon.png'))
        self.dlg.setWindowIcon(QIcon(icon_path))

        # set the tab at init
        self.dlg.IMT_Window_Tabs.setCurrentIndex(0)
        # url: http://qt-project.org/doc/qt-4.8/qtabwidget.html#resizeEvent
        self.dlg.IMT_Window_Tabs.resizeEvent = self.onResizeEvent

        # show the dialog
        self.dlg.show()

        self.init_plugin()

        # Run the dialog event loop
        self.dlg.exec_()

        self.signals_manager.disconnect_group("GUI")
        self.signals_manager.disconnect_group("WEB")

        # save GUI state in QSettings with pickle serialize module
        imt_tools.saves_states_in_qsettings_pickle(self)

    def saveState(self):
        """

        :return:
        """
        # list_id_checkbox = imt_tools.build_list_member_name_qt_checkbox(self.dlg)
        dict_state = {
            imt_tools.pickle_id_gui: {
                imt_tools.pickle_id_list_checkbox: imt_tools.serialize_list_checkbox(self.dlg, self.list_id_checkbox),
                imt_tools.pickle_id_list_tabs_size: imt_tools.serialize_tabs_size(self),
            }
        }
        return dict_state

    def restoreState(self, state, b_synchro=True):
        """

        :param state:
        :return:
        """
        # list_id_checkbox = imt_tools.build_list_member_name_qt_checkbox(self.dlg)
        #
        imt_tools.update_list_checkbox_from_serialization(self.dlg, self.list_id_checkbox, state)
        #
        imt_tools.update_tabs_size_from_serialization(self, state)
        #
        if b_synchro:
            self._synchronize_gui_and_plugin()

    def getState(self):
        """

        :return:
        """
        return self.states

    def __getstate__(self):
        """

        :return:
        """
        return self.saveState()

    def __setstate__(self, states):
        """

        :param states:
        :return:
        """
        self.states = states

    def _synchronize_gui_and_plugin(self):
        """

        :return:
        """
        self.slot_enabled_plugin()

    def init_plugin(self):
        """ Init the plugin
        - Set defaults values in QSetting # note : some value are already setted ! 
        - Setup the GUI
        """
        qgis_log_tools.logMessageINFO("Launch 'init_plugin(...)' ...")

        self.dlg.enablePlugin.setEnabled(True)

        # load GUI state in QSettings with pickle serialize module
        imt_tools.restore_states_from_pickle(self)

        self.slot_returnPressed_threshold()
        #
        self.slot_refreshComboBoxLayers()
        #
        self.autosave.update()
        self.trafipollu.update()

    def init_signals(self):
        """

        :return:
        """
        self.init_signals_gui()

    def init_signals_gui(self):
        """

        :return:
        """
        # Connections
        # activate/desactivate :
        # - plugin
        # - autosave
        # - tracking position
        self.signals_manager.add_clicked(self.dlg.enablePlugin, self.slot_enabled_plugin, "GUI")

        self.autosave.init()
        self.trafipollu.init()

        self.signals_manager.add_clicked(self.dlg.enableTrackPosition, self.slot_enabled_trackposition, "GUI")
        # box for tracking layers
        self.signals_manager.add_clicked(self.dlg.refreshLayersListForTrackPosition,
                                         self.slot_refreshComboBoxLayers,
                                         "GUI")
        #
        self.signals_manager.add(self.dlg.trackingPositionLayerCombo,
                                 "currentIndexChanged (const QString &)",
                                 self.slot_currentIndexChanged,
                                 "GUI")
        self.signals_manager.add(self.dlg.IMT_Window_Tabs,
                                 "currentChanged (int)",
                                 self.slot_currentChanged_tabs,
                                 "GUI")
        # Dev Debug
        self.signals_manager.add_clicked(self.dlg.enableLogging, self.slot_enable_logging, "GUI")
        self.signals_manager.add_clicked(self.dlg.enableUseMutexForTP, self.slot_enable_asynch, "GUI")
        # hide the window plugin
        # don't change the state (options) of the plugin
        self.signals_manager.add_clicked(self.dlg.buttonHide, self.slot_hide_plugin, "GUI")
        #
        self.signals_manager.add(self.dlg.threshold_extent,
                                 "returnPressed ()",
                                 self.slot_returnPressed_threshold,
                                 "GUI")

    def disconnect_signal_extentsChanged(self):
        """ Disconnect the signal: 'Canvas Extents Changed' of the QGIS MapCanvas """
        #
        self.signals_manager.disconnect(self.mapCanvas, "extentsChanged()")
        #
        qgis_log_tools.logMessageINFO("Disconnect SIGNAL on QGISMapCanvas")

    def connect_signal_qgis(self, qgis_object, signal_signature, slot):
        """

        :param qgis_object:
        :param signal_signature:
        :param slot:
        :return:
        """
        if qgis_object:
            self.signals_manager.add(qgis_object,
                                     signal_signature,
                                     slot,
                                     "QGIS")

    def connect_signal_extentsChanged(self):
        """ Connect the signal: 'Extent Changed' to the QGIS MapCanvas """
        self.connect_signal_qgis(self.mapCanvas, "extentsChanged()", self.slot_extentsChanged)
        #
        qgis_log_tools.logMessageINFO("Connect SIGNAL on QGISMapCanvas")

    def qgisInterfaceProjectRead(self):
        """ Action when the signal: 'Project Read' from QGIS Inteface is emitted&captured """
        pass

    def slot_layerModified(self):
        """ Action when the signal: 'Layer Modified' from QGIS Layer (current) is emitted&captured
        We connect a new signal: 'RenderComplete' to perform operation after the QGIS rendering (deferred strategy)

        """
        #
        if None != self.currentLayer:
            if None != self.mapCanvas:
                #
                self.signals_manager.add(
                    self.mapCanvas,
                    "renderComplete(QPainter*)",
                    self.slot_renderComplete_layerModified
                )
                #
                qgis_log_tools.logMessageINFO("Detect modification on layer:" + self.currentLayer.name())

    def slot_renderComplete_layerModified(self):
        """ Action when the signal: 'Render Complete' from QGIS Layer (current) is emitted&captured (after emitted&captured signal: 'Layer Modified') """
        #
        self.signals_manager.disconnect(self.mapCanvas, "renderComplete(QPainter*)")
        #
        qgis_layer_tools.commit_changes_and_refresh(self.currentLayer, self.iface, self.qsettings)

    def slot_extentsChanged(self):
        """ Action when the signal: 'Extent Changed' from QGIS MapCanvas is emitted&captured
         We connect a new signal: 'RenderComplete' to perform operation after the QGIS rendering (deferred strategy)

        """
        if self.b_use_asynch:
            self.update_track_position_with_qtimers()
        else:
            self.signals_manager.add(self.mapCanvas,
                                     "renderComplete(QPainter*)",
                                     self.slot_renderComplete_extentsChanged)

    def slot_renderComplete_extentsChanged(self):
        """ Action when the signal: 'Render Complete' from QGIS MapCanvas is emitted&captured (after a emitted&captured signal: 'Extent Changed')

        """
        #
        self.signals_manager.disconnect(self.mapCanvas, "renderComplete(QPainter*)")

        if self.b_use_asynch:
            self.update_track_position_with_qtimers()
        else:
            self.update_track_position()

    @staticmethod
    def filter_layer_for_tracking_position(layer):
        # set Attributes for Layer in DB
        # On recupere automatiquement le nombre de champs qui compose les features presentes dans ce layer
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

    def slot_currentIndexChanged(self, layer_name):
        """

        :param layer_name:
        :return:

        """
        qgis_log_tools.logMessageINFO("Launch 'currentIndexChangedTPLCB(self, layer_name=" + layer_name + ")' ...")
        # layer_name == "" when when we clear the combobox (for example)
        # if layer_name == "":
        #     return

        # noinspection PyBroadException
        try:
            layer_for_tp = imt_tools.find_layer_in_qgis_legend_interface(self.iface, layer_name)
            self.tp_layer = layer_for_tp  # set the layer for tracking position (plugin)

            list_id_fields = qgis_layer_tools.filter_layer_trackingposition_required_fields(layer_for_tp)

            self.tp_id_user_id = list_id_fields[0]
            self.tp_id_w_time = list_id_fields[1]

            data_provider = layer_for_tp.dataProvider()

            # Return a map of indexes with field names for this layer.
            # url: http://qgis.org/api/classQgsVectorDataProvider.html#a53f4e62cb05889ecf9897fc6a015c296
            fields = data_provider.fields()

            # set the fields
            # reset all fields in None
            self.values = [None for i in range(fields.count())]
            # set user_id field (suppose constant for a layer (in QGIS session))
            self.values[self.tp_id_user_id] = self.tp_user_name
        except:
            pass

    def slot_refreshComboBoxLayers(self):
        """ Action when the Combo Box attached to refreshing layers for tracking position is clicked """
        #
        qgis_log_tools.logMessageINFO("Launch 'refreshComboBoxLayers(...)' ...")
        #
        defaultSearchLayer = self.dlg.trackingPositionLayerCombo.currentText()
        # qgis_log_tools.logMessageINFO("++++ defaultSearchLayer: " + defaultSearchLayer)

        self.dlg.trackingPositionLayerCombo.clear()

        idComboBoxIndex = -1
        idComboBoxForDefaultSearchLayer = -1

        # dictionnary to link id on combobox and objects QGIS layer
        dict_key_comboboxindex_value_layer = {}
        #
        layers = self.qgsmap_layer_registry.mapLayers().values()
        for layer in layers:
            # filter on layers to add in combobox
            if qgis_layer_tools.filter_layer_for_trackingposition(layer):

                idComboBoxIndex = self.dlg.trackingPositionLayerCombo.count()
                dict_key_comboboxindex_value_layer[idComboBoxIndex] = layer
                self.dlg.trackingPositionLayerCombo.addItem(layer.name(), layer)

                # # default search layer
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
            self.tp_layer = dict_key_comboboxindex_value_layer[idComboBoxIndex]
            qgis_log_tools.logMessageINFO("Set the layer to: " + self.tp_layer.name())
        else:
            self.tp_layer = None
            #
            self.disable_trackposition()
            #
            qgis_log_tools.logMessageWARNING("WARNING: No layer selected for Tracking Position !")

    def stop_threads(self):
        """

        """
        self.signals_manager.stop_group("QTIMER")

    def enable_trackposition(self):
        #
        self.slot_refreshComboBoxLayers()
        #
        if self.tp_layer is not None:
            #
            self.connect_signal_extentsChanged()
            #
            self.signals_manager.add(self.qgsmap_layer_registry,
                                     "layersWillBeRemoved( QStringList )",
                                     self.slot_LayersWillBeRemoved,
                                     "QGIS")

    def disable_trackposition(self):
        """

        :return:
        """
        self.disconnect_signal_extentsChanged()
        #
        self.stop_threads()
        #
        self.signals_manager.disconnect(self.qgsmap_layer_registry, "layersWillBeRemoved( QStringList )")

    @DecoratorsForQt.save_checked_state(qsettings_group_name)
    def slot_enabled_trackposition(self):
        """ Action when the checkbox 'Enable Tracking Position' is clicked """
        self.enabled_trackposition()

    def enabled_trackposition(self):
        """

        """
        qgis_log_tools.logMessageINFO("Launch 'enable_trackposition(...)' ...")

        if self.dlg.enableTrackPosition.isChecked():
            self.enable_trackposition()
        else:
            self.disable_trackposition()

    @DecoratorsForQt.save_checked_state(qsettings_group_name)
    def slot_enable_logging(self):
        """ Action when the checkbox 'Enable LOGging' is clicked """
        self.enable_logging()

    def enable_logging(self):
        """
        """
        qgis_log_tools.setLogging(self.dlg.enableLogging.isChecked())

    @DecoratorsForQt.save_checked_state(qsettings_group_name)
    def slot_enable_asynch(self):
        """ Action when the checkbox 'Use Mutex (for TrackingPosition) [BETA]' is clicked """
        self.enable_asynch()

    def enable_asynch(self):
        """
        - using Mutex to protect commitChange operation in multi-threads context (signals strategy)
        Beta test for:
        - using queuing requests from TrackPosition (we try to amortize the cost and effects on QGIS GUI)

        """
        self.b_use_asynch = self.dlg.enableUseMutexForTP.isChecked()

        if not (self.dlg.enableUseMutexForTP.isChecked() and self.dlg.enableTrackPosition.isChecked()):
            self.stop_threads()

    @DecoratorsForQt.save_checked_state(qsettings_group_name)
    def slot_enabled_plugin(self):
        """ Action when the checkbox 'Enable SteetGen3 Plugin' is clicked
        Activate/desactivate all options/capabilities of IMT plugin: AutoSave&Refresh, TrackPosition

        """
        self.enabled_pluging()

    def enabled_pluging(self):
        """

        """
        qgis_log_tools.logMessageINFO("Launch 'enabled_plugin(...)' ...")

        #force the plugin to be in front
        self.dlg.raise_()

        if self.dlg.enablePlugin.isChecked():
            self.enabled_pluging_GUI()
            self.autosave.enable()
        else:
            self.disabled_plugin_GUI()
            self.autosave.disable()

        self.enabled_trackposition()
        self.enable_logging()
        self.enable_asynch()
        self.trafipollu.enable()

    def enabled_pluging_GUI(self):
        """

        :return:
        """
        self.dlg.enableAutoSave.setEnabled(True)
        self.dlg.enableTrackPosition.setEnabled(True)
        self.dlg.enableLogging.setEnabled(True)
        self.dlg.enableUseMutexForTP.setEnabled(True)
        self.dlg.thresholdLabel.setEnabled(True)
        #
        self.dlg.threshold_extent.setEnabled(True)
        self.signals_manager.add(self.dlg.threshold_extent,
                                 "editingFinished ()",
                                 self.slot_returnPressed_threshold)  # use the same slot

    def disabled_plugin_GUI(self):
        """

        """
        self.dlg.enableAutoSave.setDisabled(True)
        self.dlg.enableTrackPosition.setDisabled(True)
        self.dlg.enableLogging.setDisabled(True)
        self.dlg.enableUseMutexForTP.setDisabled(True)
        self.dlg.thresholdLabel.setDisabled(True)
        self.dlg.threshold_extent.setDisabled(True)
        #
        self.signals_manager.disconnect(self.dlg.threshold_extent, "returnPressed ()")

    def slot_hide_plugin(self):
        """ [SLOT] Hide the plugin.
        Don't change the state of the plugin

        """
        #
        self.dlg.hide()

    def slot_returnPressed_threshold(self):
        """ [SLOT]
        QT Line edit changed, we get/interpret the new value (if valid)
        Format for threshold scale : 'a'[int]:'b'[int]
        We just used 'b' for scale => threshold_scale = 'b'
        """
        import re

        valid_format = True

        threshold_string = self.dlg.threshold_extent.text()
        # remove space: http://stackoverflow.com/questions/8270092/python-remove-all-whitespace-in-a-string
        threshold_string = re.sub(r"\s+", "", threshold_string, flags=re.UNICODE)
        #
        try:
            self.threshold = int(threshold_string)
        except ValueError:
            a, b = threshold_string.split(":")
            # remove character: http://stackoverflow.com/questions/1276764/stripping-everything-but-alphanumeric-chars-from-a-string-in-python
            a = re.sub(r"\D", "", a)
            b = re.sub(r"\D", "", b)
            try:
                int(a)  # just to verify the type of 'a'
                self.threshold = int(b)  # only use 'b' to change the threshold scale value
            except ValueError:
                valid_format = False  # problem with 'a'
        # Input format problem!
        if not valid_format:
            qgis_log_tools.logMessageWARNING("Invalid input for scale! Scale format input : [int]:[int] or just [int]")

        # just for visualisation purpose
        self.dlg.threshold_extent.setText("1:" + str(self.threshold))

        return self.threshold

    @staticmethod
    def get_itemData(combobox):
        """

        :param combobox:
        :return:
        """
        return combobox.itemData(combobox.currentIndex())

    @staticmethod
    def compute_frame_size(frame, dlg=None, margin_width=60):
        """

        :param dlg:
        :param frame:
        :param margin_width:
        :return:
        """
        width = frame.contentsSize().width()
        height = frame.contentsSize().height()
        #
        width += margin_width
        #
        width = max(1024, width)
        height = min(768, max(height, width * 4 / 3))
        #
        if dlg:
            dlg.resize(width, height)
        #
        return width, height

    @staticmethod
    def update_size_dlg_from_tuple(dlg, param_tuple):
        """

        :param dlg:
        :param param_tuple:
        :return:
        """
        dlg.resize(param_tuple.width, param_tuple.height)
        return param_tuple.width, param_tuple.height

    def slot_loadFinished_webview(self, ok):
        """

        :param ok:
        """

        # safe because we stop the listener of this event when we changed the tab
        webview = self.webview_current

        tuple_webview = self.webview_dict.setdefault(webview, self.webview_default_tuple)
        last_state = tuple_webview.state
        qgis_log_tools.logMessageINFO("#last_state : " + str(last_state))

        if ok:
            # we have loaded a HTML page (offline or online)
            qgis_log_tools.logMessageINFO("## WebView : OK")

            # update the QDiaglog sizes
            dlg = None
            if self.dlg.IMT_Window_Tabs.currentIndex() == self.webview_tab_index:
                dlg = self.dlg
            width, height = self.compute_frame_size(webview.page().currentFrame(),
                                                    dlg,
                                                    self.webview_margin)
            # update the tuple for this webview
            self.webview_dict[webview] = self.TP_NAMEDTUPLE_WEBVIEW(
                'online',
                width, height,
                tuple_webview.online_url,
                tuple_webview.offline_url
            )
            #
            qgis_log_tools.logMessageINFO("### width : " + str(width) + " - height : " + str(height))
        else:
            if self.webview_dict[webview].state == 'online':
                qgis_log_tools.logMessageINFO(
                    "## WebView : FAILED TO LOAD from " + str(self.webview_dict[webview].online_url))  #online_url
            else:
                qgis_log_tools.logMessageINFO(
                    "## WebView : FAILED TO LOAD from " + str(self.webview_dict[webview].offline_url))
            #
            if self.webview_dict[webview].state != 'offline':  #regular case we failed, but we are going to try again
                self.webview_dict[webview] = self.TP_NAMEDTUPLE_WEBVIEW(
                    'offline',
                    tuple_webview.width, tuple_webview.height,
                    tuple_webview.online_url,
                    tuple_webview.offline_url
                )

                # try to load the offline version (still in initial state)
                # @FIXME : doesn't load the images in offline mode on XP...
                webview.load(QUrl(tuple_webview.offline_url))

            else:  # we already failed last, time, stopping to try
                qgis_log_tools.logMessageINFO("## WebView : stopping to try to retrieve html")

    def webview_load_page(self, webview, index_tab=-1, margin=60):
        """

        :param webview:
        :param margin:
        :return:
        """
        #
        tuple_webview = self.webview_dict.setdefault(webview, self.webview_default_tuple)

        self.webview_margin = margin
        self.webview_current = webview
        self.webview_tab_index = index_tab

        # signal : 'loadFinished(bool)'
        self.signals_manager.add(webview,
                                 "loadFinished (bool)",
                                 self.slot_loadFinished_webview,
                                 "WEB")

        # reset/clear the web widget
        # url : http://qt-project.org/doc/qt-4.8/qwebview.html#settings
        web_setting = webview.settings()
        web_setting.clearMemoryCaches()
        web_setting.setAttribute(QWebSettings.PluginsEnabled, True)

        global_settings = web_setting.globalSettings()
        #
        global_settings.clearMemoryCaches()
        # Enables plugins in Web pages (e.g. using NPAPI).
        # url: http://doc.qt.io/qt-4.8/qwebsettings.html#WebAttribute-enum
        global_settings.setAttribute(QWebSettings.PluginsEnabled, True)

        if tuple_webview.state == 'offline':  # offline
            webview.load(tuple_webview.offline_url)
        else:  # 'init' or 'online'
            webview.load(tuple_webview.online_url)

    def slot_currentChanged_tabs(self, index):
        """

        :type index: int
        :param index:
        :return:
        """
        #
        self.signals_manager.disconnect_group("WEB")
        #
        # Note: convention, 'user' & 'about' are the lastest tab in IMT_Window_Tabs (QTabWidget)
        count_tabs = self.dlg.IMT_Window_Tabs.count()
        if index == count_tabs - 1:
            qgis_log_tools.logMessageINFO("## Tab : User Doc")
            self.webview_load_page(self.dlg.webView_userdoc, index, self.webview_margin)
        elif index == count_tabs - 2:
            qgis_log_tools.logMessageINFO("## Tab : About")
            self.webview_load_page(self.dlg.webView_about, index, self.webview_margin)
        else:
            self.dict_tabs_size[index] = self.dict_tabs_size.setdefault(index, self.dlg.minimumSize())
            self.dlg.resize(self.dict_tabs_size[index])

    @pyqtSlot('QStringList')
    def slot_LayersWillBeRemoved(self, theLayerIds):
        """

        :type theLayerIds: QStringList
        :param theLayerIds:
        """

        qgis_log_tools.logMessageINFO("# slot_LayersWillBeRemoved")

        if len(theLayerIds):
            for id_layer in theLayerIds:
                qgis_log_tools.logMessageINFO("id_layer: " + str(id_layer))

            tp_dict_layers_to_commit_is_empty = True
            tp_dict_key_l_values_et_is_empty = True
            tp_dict_key_l_values_listfeatures_is_empty = True

            self.tp_mutex_on_layers.lockForWrite()  # release this lock in 'slot_LayersRemoved' slot
            # clean lists, dicts

            qgis_log_tools.logMessageINFO(
                "# self.tp_queue_rt_ntuples_let.qsize() : " + str(self.tp_queue_rt_ntuples_let.qsize()))

            nb_tuples_let_removed = 0
            tp_queue_fifo_rt_ntuples_let = Queue.Queue()
            #
            while not self.tp_queue_rt_ntuples_let.empty():
                # queue in read-write-delete/pop here
                tp_tuple = self.tp_queue_rt_ntuples_let.get()
                #
                for layer_id in theLayerIds:
                    qgis_log_tools.logMessageINFO("layer_id: " + str(id_layer) +
                                                  " - tp_tuple.id_layer: " + str(tp_tuple.id_layer))
                    if layer_id != tp_tuple.id_layer:
                        tp_queue_fifo_rt_ntuples_let.put(tp_tuple)
                    else:
                        nb_tuples_let_removed += 1
                        qgis_log_tools.logMessageINFO("## tuple removed !")
            #
            # qgis_log_tools.logMessageINFO("## nb_tuples_let_removed : " + str(nb_tuples_let_removed))
            #
            while not tp_queue_fifo_rt_ntuples_let.empty():
                self.tp_queue_rt_ntuples_let.put(tp_queue_fifo_rt_ntuples_let.get())

            tp_dict_layers_to_commit_is_empty = len(self.tp_dict_layers_to_commit.keys()) == 0
            tp_dict_key_l_values_et_is_empty = len(self.tp_dict_key_l_values_et.keys()) == 0
            tp_dict_key_l_values_listfeatures_is_empty = len(self.tp_dict_key_l_values_listfeatures.keys()) == 0

            for layer_id in theLayerIds:
                if layer_id in self.tp_dict_layers_to_commit:
                    qgis_log_tools.logMessageINFO(
                        "delete key: " + str(layer_id) + "in dict: self.tp_dict_layers_to_commit")
                    del self.tp_dict_layers_to_commit[layer_id]

                if layer_id in self.tp_dict_key_l_values_et:
                    qgis_log_tools.logMessageINFO(
                        "delete key: " + str(layer_id) + "in dict: self.tp_dict_key_l_values_et")
                    del self.tp_dict_key_l_values_et[layer_id]

                if layer_id in self.tp_dict_key_l_values_listfeatures:
                    qgis_log_tools.logMessageINFO(
                        "delete key: " + str(layer_id) + "in dict: self.tp_dict_key_l_values_listfeatures")
                    del self.tp_dict_key_l_values_listfeatures[layer_id]

            if not tp_dict_layers_to_commit_is_empty and len(self.tp_dict_layers_to_commit.keys()) == 0:
                pass

            if not tp_dict_key_l_values_et_is_empty and len(self.tp_dict_key_l_values_et.keys()) == 0:
                qgis_log_tools.logMessageINFO("Need to stop QTimer : qtimer_tracking_position_memory_to_geom ! ")
                #
                self.signals_manager.stop(self.qtimer_tracking_position_memory_to_geom)

            if not tp_dict_key_l_values_listfeatures_is_empty and len(self.tp_dict_key_l_values_listfeatures.keys()) == 0:
                qgis_log_tools.logMessageINFO("Need to stop QTimer : qtimer_tracking_position_geom_to_layer ! ")
                #
                self.signals_manager.stop(self.qtimer_tracking_position_geom_to_layer)
            #
            self.signals_manager.add(self.qgsmap_layer_registry,
                                     "layersRemoved( QStringList )",
                                     self.slot_LayersRemoved)

    @pyqtSlot('QStringList')
    def slot_LayersRemoved(self, theLayerIds):
        """

        :param theLayerIds:

        """
        qgis_log_tools.logMessageINFO("# slot_LayersRemoved")
        #
        for id_layer in theLayerIds:
            qgis_log_tools.logMessageINFO("id_layer: " + str(id_layer))
            try:
                if id_layer == self.tp_layer.id():
                    qgis_log_tools.logMessageINFO("QGIS want to remove our tracking layer !")
                    self.tp_layer = None
            except:
                pass
        #
        self.tp_layer = None
        self.slot_refreshComboBoxLayers()
        #
        self.tp_mutex_on_layers.unlock()
        #
        self.signals_manager.disconnect(self.qgsmap_layer_registry, "layersRemoved()")

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

        if self.tp_layer is None:
            return -1

        mapCanvas = self.mapCanvas
        mapCanvas_extent = mapCanvas.extent()

        layer_for_polygon_extent = self.tp_layer

        if mapCanvas.scale() > self.threshold:
            qgis_log_tools.logMessageWARNING("MapCanvas extent size exceed the Threshold size for tracking")
            qgis_log_tools.logMessageWARNING(
                "-> MapCanvas extent size= " + str(max(mapCanvas_extent.width(), mapCanvas_extent.height())) +
                "\tThreshold size= " + str(self.threshold))
            return -2

        # get the list points from the current extent (from QGIS MapCanvas)
        list_points_from_mapcanvas = imt_tools.construct_listpoints_from_extent(mapCanvas_extent)

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

        if not bUseEmptyFields:
            # update the time stamp attribute
            self.values[self.tp_id_w_time] = imt_tools.get_timestamp_from_qt_string_format()

        fet.setAttributes(self.values)

        # How can I programatically create and add features to a memory layer in QGIS 1.9?
        # url: http://gis.stackexchange.com/questions/60473/how-can-i-programatically-create-and-add-features-to-a-memory-layer-in-qgis-1-9
        # write the layer and send request to DB
        layer_for_polygon_extent.startEditing()
        layer_for_polygon_extent.addFeatures([fet], False)  # bool_makeSelected=False
        #
        result_commit = layer_for_polygon_extent.commitChanges()
        #
        if result_commit:
            qgis_log_tools.logMessageINFO("Location saved in layer: " + layer_for_polygon_extent.name())
        else:
            qgis_log_tools.logMessageCRITICAL(
                "saving position failed : are you sure the selected tracking layer: " + layer_for_polygon_extent.name() +
                "has at least 2 attributes : \"user_id\"::text and \"w_time\"::text")
            #
            commitErrorString = layer_for_polygon_extent.commitErrors()[2]
            #
            interval = [commitErrorString.rfind(":") + 2,   # start :  +2 to skip ': ' prefix of commitError msg
                        len(commitErrorString)]             # end
            commitErrorStringShort = commitErrorString[interval[0]:interval[1]]
            #
            self.iface.messageBar().pushMessage("IMT. ERROR : " + "\"" + commitErrorStringShort + "\"",
                                                "",
                                                QgsMessageBar.CRITICAL, 0)
        #
        return result_commit

    def update_track_position_with_qtimers(self, bWithProjectionInCRSLayer=True, bUseEmptyFields=False):
        """
        Note: it's not a Thread/QTimer

        :param bWithProjectionInCRSLayer:
        :param bUseEmptyFields:
        :return:
        """
        qgis_log_tools.logMessageINFO("update_track_position_with_qtimers")

        bIsTimeToUpdate = self.tp_timers.is_time_to_update("update_track_position_with_qtimers",
                                                           "tp_threshold_time_for_realtime_tracking_position")
        if bIsTimeToUpdate:
            # Do we have a current layer activate for tracking position ?
            if self.tp_layer is None:
                # if not, no need to go further
                return -1

            mapCanvas = self.mapCanvas
            mapcanvas_extent = mapCanvas.extent()

            # Add a filter to prevent to save the same extent (useful in regards to our 'dummy' approach to refresh map)
            if imt_tools.extent_equal(self.tp_last_extent_saved, mapcanvas_extent, 0.01):  # 1.0 %
                return -3

            # Filter on extent map scale (size)
            # We use a threshold scale (user input in the GUI)
            if mapCanvas.scale() > self.threshold:
                qgis_log_tools.logMessageWARNING("MapCanvas extent scale exceed the Threshold scale for tracking")
                qgis_log_tools.logMessageWARNING(
                    "-> MapCanvas scale= " + str(mapCanvas.scale()) +
                    "\tThreshold scale= " + str(self.threshold))
                return -2

            with QReadLocker(self.tp_mutex_on_layers):
                layer_for_itp = self.tp_layer
                try:
                    id_layer_for_itp = layer_for_itp.id()

                    # Build the tuple contains:
                    # - layer used for tracking position
                    # - list of points extract from the current extent for QGIS Map Canvas
                    # - acquisition time for this track
                    rt_ntuple = self.TP_NAMEDTUPLE_LET(
                        id_layer_for_itp,
                        imt_tools.construct_listpoints_from_extent(mapcanvas_extent),
                        imt_tools.get_timestamp()
                    )

                    qgis_log_tools.logMessageINFO("## id_layer_for_itp : " + str(id_layer_for_itp))

                    # This queue is not protect (multi-threads context)
                    # but it's oki in your case
                    # queue in write-append only here !
                    self.tp_queue_rt_ntuples_let.put(rt_ntuple)
                except:
                    qgis_log_tools.logMessageWARNING("update_track_position_with_qtimers : exception here !")
                    pass

            self.tp_last_extent_saved = mapcanvas_extent

            self.tp_timers.update("update_track_position_with_qtimers")

            interval = self.tp_timers.get_delay("tp_threshold_time_for_tp_to_mem")
            self.signals_manager.start(self.qtimer_tracking_position_rtt_to_memory, interval)

        # update timer for still moving here !
        self.tp_timers.update("still moving")

        return 1

    def slot_tp_rttp_to_memory(self):
        """ Action perform when the QTimer for Tracking Position is time out
        Enqueue requests from Tracking Position to amortize the cost&effect on QGIS GUI

        This pass transfer events inputs map moving into memory (QGIS -> Python)
        """
        qgis_log_tools.logMessageINFO("~~ CALL : tracking_position_qtimer_rttp_to_memory ~~")

        with QReadLocker(self.tp_mutex_on_layers):
            # this queue is not protect (multi-threads context)
            # but it's oki in your case
            size_tp_queue = self.tp_queue_rt_ntuples_let.qsize()

            while not self.tp_queue_rt_ntuples_let.empty():
                # queue in read-write-delete/pop here
                tp_tuple = self.tp_queue_rt_ntuples_let.get()
                self.tp_queue_rt_ntuples_let.task_done()

                # url: http://stackoverflow.com/questions/20585920/how-to-add-multiple-values-to-a-dictionary-key-in-python
                self.tp_dict_key_l_values_et.setdefault(tp_tuple.id_layer, []).append(
                    self.TP_NAMEDTUPLE_ET(tp_tuple.extent, tp_tuple.w_time)
                )

            if size_tp_queue != 0:
                qgis_log_tools.logMessageINFO("** Pack " + str(size_tp_queue) + " tuples for 1 call -> mem")

        #####################
        # Process Management
        #####################
        self.signals_manager.stop(self.qtimer_tracking_position_rtt_to_memory)
        #
        interval = self.tp_timers.get_delay("tp_threshold_time_for_construct_geom")
        self.signals_manager.start(self.qtimer_tracking_position_memory_to_geom, interval)
        #####################

    def slot_memory_to_geom_tp(self):
        """ Action perform when the QTimer for Tracking Position is time out
        Enqueue requests from Tracking Position to amortize the cost&effect on QGIS GUI

        This pass convert tracking extents datas (MEMory side) to QGIS GEOMetries (MEMory side)
        In this pass we project the entries points in world (QGIS) CRS into CRS of the layer target (for tracking position)
        """
        qgis_log_tools.logMessageINFO("~~ CALL : tracking_position_qtimer_memory_to_geom ~~")

        mapCanvas = self.mapCanvas

        # url: http://qgis.org/api/classQgsMapCanvas.html#af0ffae7b5e5ec8b29764773fa6a74d58
        extent_src_crs = mapCanvas.mapSettings().destinationCrs()

        append_in_dic = False

        with QReadLocker(self.tp_mutex_on_layers):
            for id_layer in self.tp_dict_key_l_values_et.keys():
                layer = self.qgsmap_layer_registry.mapLayer(id_layer)
                layer_to_commit = layer

                # url: http://qgis.org/api/classQgsMapLayer.html#a40b79e2d6043f8ec316a28cb17febd6c
                extent_dst_crs = layer_to_commit.crs()
                # url: http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/crs.html
                xform = QgsCoordinateTransform(extent_src_crs, extent_dst_crs)

                tp_list_fets = []

                # pop key from tracking position dictionary
                list_ntuples = self.tp_dict_key_l_values_et.pop(id_layer)
                if len(list_ntuples) != 0:
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
                        # append_at_least_1_fet = True

                    self.tp_dict_key_l_values_listfeatures.setdefault(id_layer, []).append(tp_list_fets)
                    append_in_dic = True
                    #
                    qgis_log_tools.logMessageINFO(
                        "-- Pack " + str(len(tp_list_fets)) + " features in layer: " + layer.name())

        if append_in_dic:
            #####################
            # Process Management
            #####################
            self.signals_manager.stop(self.qtimer_tracking_position_memory_to_geom)
            #
            interval = self.tp_timers.get_delay("tp_threshold_time_for_sending_geom_to_layer")
            interval += CONVERT_S_TO_MS(max(0.0, (
                self.tp_timers.get_delay("delay_time_still_moving") - self.tp_timers.delta_with_current_time(
                    "still moving"))))
            self.signals_manager.start(self.qtimer_tracking_position_geom_to_layer, interval)
            #####################

    def slot_geom_to_layer_tp(self):
        """ Action perform when the QTimer for Tracking Position is time out
        Enqueue requests from Tracking Position to amortize the cost&effect on QGIS GUI

        In this pass we transfer if timeout for delay is done and we 'not moving' on QGIS Map
        QGIS GEOmetries [MEM] into target Layer [MEM]
        This operation send/render geometries into the Layer (we see a rectangle representation of our extent on the screen)
        """
        qgis_log_tools.logMessageINFO("~~ CALL : tracking_position_qtimer_geom_to_layer ~~")

        bNotMovingOnQGISMap = self.tp_timers.is_time_to_update("still moving", "delay_time_still_moving")

        if bNotMovingOnQGISMap:
            append_in_dict_one_time = False

            with QReadLocker(self.tp_mutex_on_layers):

                for id_layer in self.tp_dict_key_l_values_listfeatures.keys():
                    # from the dict we retrieve a list of list
                    tp_list_of_list_fets = self.tp_dict_key_l_values_listfeatures.pop(id_layer)

                    layer = self.qgsmap_layer_registry.mapLayer(id_layer)
                    try:
                        # How can I programatically create and add features to a memory layer in QGIS 1.9?
                        # url: http://gis.stackexchange.com/questions/60473/how-can-i-programatically-create-and-add-features-to-a-memory-layer-in-qgis-1-9
                        # write the layer and send request to DB
                        layer.startEditing()
                        for tp_list_fets in tp_list_of_list_fets:
                            layer.addFeatures(tp_list_fets, False)  # bool_makeSelected=False

                        qgis_log_tools.logMessageINFO(
                            "++ Pack requests => " + str(
                                len(tp_list_of_list_fets)) + " extents for layer: " + layer.name())
                    except:
                        qgis_log_tools.logMessageWARNING("tracking_position_qtimer_geom_to_layer : exception here !")
                        pass

                    self.tp_dict_layers_to_commit[id_layer] = 1
                    append_in_dict_one_time = True

            if append_in_dict_one_time:
                #####################
                # Process Management
                #####################
                self.signals_manager.stop(self.qtimer_tracking_position_geom_to_layer)
                #
                interval = self.tp_timers.get_delay("tp_threshold_time_for_sending_layer_to_dp")
                interval_still_moving = self.tp_timers.get_delay("delay_time_still_moving") - \
                                        self.tp_timers.delta_with_current_time("still moving")
                interval += CONVERT_S_TO_MS(max(0.0, interval_still_moving))
                self.signals_manager.start(self.qtimer_tracking_position_layers_to_commit, interval)
                #####################
        else:
            self.qtimer_tracking_position_geom_to_layer.setInterval(CONVERT_S_TO_MS(self.tp_timers.get_delay("delay_time_still_moving")))

    @staticmethod
    def _commit_layer_(iface, layer_to_commit):
        """

        :param layer_to_commit:
        :return:
        """
        #
        try:
            if layer_to_commit.commitChanges():
                qgis_log_tools.logMessageINFO("* Commit change layer:" +
                                              layer_to_commit.name() +
                                              " [OK]")
            else:
                #
                commit_error_string = layer_to_commit.commitErrors()[2]
                #
                # start :  +2 to skip ': ' prefix of commitError msg
                commit_error_string_short = commit_error_string[commit_error_string.rfind(":") + 2:]
                #
                iface.messageBar().pushMessage("IMT. ERROR : " + "\"" + commit_error_string_short + "\"",
                                               "",
                                               QgsMessageBar.CRITICAL, 0)
        except Exception, err:
            qgis_log_tools.logMessageWARNING("exception here !")
            import sys
            qgis_log_tools.logMessageWARNING("Unexpected error: " + str(err))

    def slot_layers_to_commit_tp(self):
        """Action perform when the QTimer for Tracking Position is time out
         Enqueue requests from Tracking Position to amortize the cost&effect on QGIS GUI

         In this pass, we commit QGIS Layer into Data Provider (PostGIS DataBase, or ShapeFile, or anything (local or distant)
         MEM -> DP
         """
        qgis_log_tools.logMessageINFO("~~ CALL : tracking_position_qtimer_layers_to_commit ~~")
        #
        bNotMovingOnQGISMap = self.tp_timers.is_time_to_update("still moving", "delay_time_still_moving")
        #
        if bNotMovingOnQGISMap:
            with QReadLocker(self.tp_mutex_on_layers):
                id_layers = self.tp_dict_layers_to_commit.keys()
                # clear dict
                self.tp_dict_layers_to_commit.clear()

                for id_layer_to_commit in id_layers:
                    layer_to_commit = self.qgsmap_layer_registry.mapLayer(id_layer_to_commit)
                    #
                    self._commit_layer_(self.iface, layer_to_commit)
            #####################
            # Process Management
            #####################
            # last link of processes chain
            self.signals_manager.stop(self.qtimer_tracking_position_layers_to_commit)
            #####################
        else:
            #####################
            # Process Management
            #####################
            interval = CONVERT_S_TO_MS(self.tp_timers.get_delay("delay_time_still_moving"))
            self.qtimer_tracking_position_layers_to_commit.setInterval(interval)
            #####################
