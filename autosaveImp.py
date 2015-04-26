__author__ = 'atty'

from PyQt4.QtCore import QSettings

import qgis_layer_tools
import qgis_log_tools
from signalsmanager import SignalsManager
from decorators import DecoratorsForQt



# super() fails with error: TypeError "argument 1 must be type, not classobj"
# url: http://stackoverflow.com/questions/1713038/super-fails-with-error-typeerror-argument-1-must-be-type-not-classobj
class AutoSaveImp(object):
    """

    """
    def __init__(self, iface, dlg):
        """

        """
        self.__iface = iface
        self.__dlg = dlg
        self.__mapCanvas = self.__iface.mapCanvas()
        self.__signals_manager = SignalsManager.instance()
        self.__active_layer = None

    def _get_dlg(self):
        """

        :return:
        """
        return self.__dlg

    def _init_signals(self):
        """

        """
        self.__signals_manager.add_clicked(self.__dlg, self._slot_clicked_checkbox_autosave, "GUI")
        #
        self.__connect_signal_currentLayerChanged()

    def _enable_autosave(self):
        """
        Connection with QGIS interface
        """
        self.__connect_signal_currentLayerChanged()
        #
        self.__action_enable_autosave()

    def _disable_autosave(self):
        """
        Disconnection with QGIS interface
        """
        self.__disconnect_signal_currentLayerChanged()
        #
        if self.__active_layer is not None:
            self.__disconnect_signal_layerModified(self.__active_layer)

    @DecoratorsForQt.save_checked_state("IMT")
    def _slot_clicked_checkbox_autosave(self):
        """ Action when the checkbox 'Enable Auto-Save and Refresh' is clicked """
        #
        self.__action_enable_autosave()

    def __action_enable_autosave(self):
        #
        qgis_log_tools.logMessageINFO("Launch 'enable_autosave(...)' ...")
        #
        if self.__dlg.isChecked():
            self._update_current_layer()
            #
            if self.__active_layer is not None:
                self._connect_signal_layerModified_(self.__active_layer)
        else:
            if self.__active_layer is not None:
                self.__disconnect_signal_layerModified(self.__active_layer)

    def _update_current_layer(self):
        """

        :return:
        """
        return_value = False
        try:
            # filtre sur les layers
            # if qgis_layer_tools.filter_layer_for_imt(self.iface.activeLayer():
            if qgis_layer_tools.filter_layer_for_imt(self.__iface.activeLayer(),
                                                     [qgis_layer_tools.filter_layer_vectorlayer]):  # TODO: just windows testing
                #
                qgis_log_tools.logMessageINFO("Active layer: " + self.__iface.activeLayer().name()
                                              + "is 'compatible' for Auto-Saving !"
                                              + "- [OK]")
                #
                self.__active_layer = self.__iface.activeLayer()
                #
                return_value = True
            else:
                qgis_log_tools.logMessageWARNING("Active layer: " + self.__iface.activeLayer().name()
                                                 + "is not 'compatible' for Auto-Saving ! (VectorLayer + PostGIS)"
                                                 + "- [FAILED]")
                #
                self.__active_layer = None
        except:
            qgis_log_tools.logMessageINFO("Exception here!")
        #
        return return_value

    def _connect_signal_layerModified_(self, layer):
        """ Connect the signal: "Layer Modified" to the layer given

        :param layer: QGIS layer
        :type layer: QgsMapLayer

        """
        if layer is not None:
            self.__signals_manager.add(layer,
                                     "layerModified()",
                                     self.__slot_layerModified,
                                     "QGIS")
            #
            qgis_log_tools.logMessageINFO("Connect SIGNAL on layer: " + layer.name())

    def __disconnect_signal_layerModified(self, layer):
        """ Disconnect the signal: 'Layer Modified' of the layer given

        :param layer: QGIS Layer
        :type layer: QgsMapLayer

        """
        if layer is not None:
            self.__signals_manager.disconnect(layer, "layerModified()")
            #
            qgis_log_tools.logMessageINFO("Disconnect SIGNAL on layer: " + layer.name())

    def __slot_layerModified(self):
        """ Action when the signal: 'Layer Modified' from QGIS Layer (current) is emitted&captured
        We connect a new signal: 'RenderComplete' to perform operation after the QGIS rendering (deferred strategy)

        """
        #
        # if self.currentLayer is not None and self.mapCanvas is not None:
        #
        #
        self.__signals_manager.add(
            self.__mapCanvas,
            "renderComplete(QPainter*)",
            self.__slot_renderComplete_layerModified
        )
        qgis_log_tools.logMessageINFO("Detect modification on layer:" + self.__active_layer.name())

    def __slot_renderComplete_layerModified(self):
        """ Action when the signal: 'Render Complete' from QGIS Layer (current) is emitted&captured (after emitted&captured signal: 'Layer Modified') """
        #
        self.__signals_manager.disconnect(self.__mapCanvas, "renderComplete(QPainter*)")
        #
        qgis_layer_tools.commit_changes_and_refresh(self.__active_layer, self.__iface, QSettings())

    def __connect_signal_currentLayerChanged(self):
        """ Connect the signal: 'Layer Changed' to the layer given """
        self.__connect_signal_qgis(self.__iface, "currentLayerChanged(QgsMapLayer*)", self.__slot_currentLayerChanged)
        #
        qgis_log_tools.logMessageINFO("Connect SIGNAL on QGISInterface")

    def __disconnect_signal_currentLayerChanged(self):
        """ Disconnect the signal: 'Current Layer Changed' of the QGIS Interface"""
        #
        self.__signals_manager.disconnect(self.__iface, "currentLayerChanged(QgsMapLayer*)")
        #
        qgis_log_tools.logMessageINFO("Disconnect SIGNAL on QGISInterface")

    def __connect_signal_qgis(self, qgis_object, signal_signature, slot):
        """

        :param qgis_object:
        :param signal_signature:
        :param slot:

        """
        if qgis_object:
            self.__signals_manager.add(qgis_object,
                                     signal_signature,
                                     slot,
                                     "QGIS")

    def __slot_currentLayerChanged(self, layer):
        """ Action when the signal: 'Current Layer Changed' from QGIS MapCanvas is emitted&captured

        :param layer: QGIS layer -> current layer using by Interactive_Map_Tracking plugin
        :type layer: QgsMapLayer

        """
        # disconnect the current layer
        if None != self.__active_layer:
            self.__disconnect_signal_layerModified(self.__active_layer)

        #
        self._update_current_layer()

        if self.__active_layer is not None:
            #
            if self.__dlg.isChecked():
                qgis_layer_tools.commit_changes_and_refresh(self.__active_layer, self.__iface, QSettings())
                self._connect_signal_layerModified_(self.__active_layer)
                #
                qgis_log_tools.logMessageINFO("Change Layer: self.currentLayer.name()=" + self.__active_layer.name())
        else:
            qgis_log_tools.logMessageINFO("No layer selected (for ITP)")