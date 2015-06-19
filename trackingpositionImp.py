__author__ = 'atty'

from signalsmanager import SignalsManager
import imt_tools
from PyQt4.QtCore import QTimer
import Queue
from collections import namedtuple
import time
import qgis_log_tools
import qgis_layer_tools
from decorators import DecoratorsForQt
from PyQt4.QtCore import QReadWriteLock, QReadLocker, pyqtSlot
from qgis.core import QgsMapLayerRegistry, QgsCoordinateTransform, QgsGeometry, QgsFeature, QgsRectangle
from qgis.gui import QgsMessageBar


class TrackingPositionImp(object):

    """

    """

    qsettings_group_name = "IMT"

    def __init__(self, iface, dlg):
        """

        """
        self.iface = iface
        self.dlg = dlg
        self.mapCanvas = self.iface.mapCanvas()
        self.qgsmap_layer_registry = QgsMapLayerRegistry.instance()
        #
        self.signals_manager = SignalsManager.instance()
        #
        self.tp_layer = None

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

        # OPTIONS: timing reactions
        #
        self.tp_timers = imt_tools.TpTimer()
        # TODO : add this options timing on GUI
        # in S
        tp_threshold_time_for_realtime_tracking_position = imt_tools.convert_freq_to_sec(8)  # i.e. 8hz => (max) 8 tracking positions record per second
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
        current_time = time.time()
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

        # LOCKER for protecting layers (ptr) from QGIS
        # used by our asynchronous tracking method
        # -> to ensure protection when/if user want to delete the tracking layer
        self.tp_mutex_on_layers = QReadWriteLock()

        self.tp_last_extent_saved = QgsRectangle()

    def _init_signals_(self):
        """

        """
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

            # save history of extents (used for filtering)
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

            if size_tp_queue:
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
            interval += imt_tools.convert_s_to_ms(max(0.0, (
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
                interval += imt_tools.convert_s_to_ms(max(0.0, interval_still_moving))
                self.signals_manager.start(self.qtimer_tracking_position_layers_to_commit, interval)
                #####################
        else:
            self.qtimer_tracking_position_geom_to_layer.setInterval(
                imt_tools.convert_s_to_ms(self.tp_timers.get_delay("delay_time_still_moving"))
            )

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
            interval = imt_tools.convert_s_to_ms(self.tp_timers.get_delay("delay_time_still_moving"))
            self.qtimer_tracking_position_layers_to_commit.setInterval(interval)
            #####################

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
            # self.values[self.tp_id_user_id] = self.tp_user_name
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
            # self.signals_manager.add(self.qgsmap_layer_registry,
            #                          "layersWillBeRemoved( QStringList )",
            #                          self.slot_LayersWillBeRemoved,
            #                          "QGIS")
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

    def slot_extentsChanged(self):
        """ Action when the signal: 'Extent Changed' from QGIS MapCanvas is emitted&captured
         We connect a new signal: 'RenderComplete' to perform operation after the QGIS rendering (deferred strategy)

        """
        # if self.b_use_asynch:
        #     # self.update_track_position_with_qtimers()
        #     self.trackposition.update_track_position_with_qtimers()
        # else:
        #     self.signals_manager.add(self.mapCanvas,
        #                              "renderComplete(QPainter*)",
        #                              self.slot_renderComplete_extentsChanged)
        self.update_track_position_with_qtimers()

    def slot_renderComplete_extentsChanged(self):
        """ Action when the signal: 'Render Complete' from QGIS MapCanvas is emitted&captured (after a emitted&captured signal: 'Extent Changed')

        """
        self.signals_manager.disconnect(self.mapCanvas, "renderComplete(QPainter*)")
        self.update_track_position_with_qtimers()

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