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
        self._iface_ = iface
        self._dlg_ = dlg
        self._mapCanvas_ = self._iface_.mapCanvas()
        # self._signals_manager_ = SignalsManager.getInstance()
        self._signals_manager_ = SignalsManager.instance()
        self._active_layer_ = None

    def _init_signals_(self):
        """

        """
        self._signals_manager_.add_clicked(self._dlg_, self.slot_clicked_checkbox_autosave, "GUI")
        #
        self._connect_signal_currentLayerChanged_()

    def _enable_autosave_(self):
        """
        Connection with QGIS interface
        """
        self._connect_signal_currentLayerChanged_()
        #
        self.enable_autosave()

    def _disable_autosave_(self):
        """
        Disconnection with QGIS interface
        """
        self._disconnect_signal_currentLayerChanged_()
        #
        if self._active_layer_ is not None:
            self._disconnect_signal_layerModified_(self._active_layer_)

    @DecoratorsForQt.save_checked_state("IMT")
    def slot_clicked_checkbox_autosave(self):
        """ Action when the checkbox 'Enable Auto-Save and Refresh' is clicked """
        #
        self.enable_autosave()

    def enable_autosave(self):
        #
        qgis_log_tools.logMessageINFO("Launch 'enable_autosave(...)' ...")
        #
        if self._dlg_.isChecked():
            self._update_current_layer_()
            #
            if self._active_layer_ is not None:
                self._connect_signal_layerModified_(self._active_layer_)
        else:
            if self._active_layer_ is not None:
                self._disconnect_signal_layerModified_(self._active_layer_)

    def _update_current_layer_(self):
        """

        :return:
        """
        return_value = False
        try:
            # filtre sur les layers
            # if qgis_layer_tools.filter_layer_for_imt(self.iface.activeLayer():
            if qgis_layer_tools.filter_layer_for_imt(self._iface_.activeLayer(),
                                                     [qgis_layer_tools.filter_layer_vectorlayer]):  # for test
                #
                qgis_log_tools.logMessageINFO("Active layer: " + self._iface_.activeLayer().name()
                                              + "is 'compatible' for Auto-Saving !"
                                              + "- [OK]")
                #
                self._active_layer_ = self._iface_.activeLayer()
                #
                return_value = True
            else:
                qgis_log_tools.logMessageWARNING("Active layer: " + self._iface_.activeLayer().name()
                                                 + "is not 'compatible' for Auto-Saving ! (VectorLayer + PostGIS)"
                                                 + "- [FAILED]")
                #
                self._active_layer_ = None
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
            self._signals_manager_.add(layer,
                                     "layerModified()",
                                     self._slot_layerModified_,
                                     "QGIS")
            #
            qgis_log_tools.logMessageINFO("Connect SIGNAL on layer: " + layer.name())

    def _disconnect_signal_layerModified_(self, layer):
        """ Disconnect the signal: 'Layer Modified' of the layer given

        :param layer: QGIS Layer
        :type layer: QgsMapLayer

        """
        if layer is not None:
            self._signals_manager_.disconnect(layer, "layerModified()")
            #
            qgis_log_tools.logMessageINFO("Disconnect SIGNAL on layer: " + layer.name())

    def _slot_layerModified_(self):
        """ Action when the signal: 'Layer Modified' from QGIS Layer (current) is emitted&captured
        We connect a new signal: 'RenderComplete' to perform operation after the QGIS rendering (deferred strategy)

        """
        #
        # if self.currentLayer is not None and self.mapCanvas is not None:
        #
        #
        self._signals_manager_.add(
            self._mapCanvas_,
            "renderComplete(QPainter*)",
            self._slot_renderComplete_layerModified_
        )
        qgis_log_tools.logMessageINFO("Detect modification on layer:" + self._active_layer_.name())

    def _slot_renderComplete_layerModified_(self):
        """ Action when the signal: 'Render Complete' from QGIS Layer (current) is emitted&captured (after emitted&captured signal: 'Layer Modified') """
        #
        self._signals_manager_.disconnect(self._mapCanvas_, "renderComplete(QPainter*)")
        #
        qgis_layer_tools.commit_changes_and_refresh(self._active_layer_, self._iface_, QSettings())

    def _connect_signal_currentLayerChanged_(self):
        """ Connect the signal: 'Layer Changed' to the layer given """
        self._connect_signal_qgis_(self._iface_, "currentLayerChanged(QgsMapLayer*)", self._slot_currentLayerChanged_)
        #
        qgis_log_tools.logMessageINFO("Connect SIGNAL on QGISInterface")

    def _disconnect_signal_currentLayerChanged_(self):
        """ Disconnect the signal: 'Current Layer Changed' of the QGIS Interface"""
        #
        self._signals_manager_.disconnect(self._iface_, "currentLayerChanged(QgsMapLayer*)")
        #
        qgis_log_tools.logMessageINFO("Disconnect SIGNAL on QGISInterface")

    def _connect_signal_qgis_(self, qgis_object, signal_signature, slot):
        """

        :param qgis_object:
        :param signal_signature:
        :param slot:

        """
        if qgis_object:
            self._signals_manager_.add(qgis_object,
                                     signal_signature,
                                     slot,
                                     "QGIS")

    def _slot_currentLayerChanged_(self, layer):
        """ Action when the signal: 'Current Layer Changed' from QGIS MapCanvas is emitted&captured

        :param layer: QGIS layer -> current layer using by Interactive_Map_Tracking plugin
        :type layer: QgsMapLayer

        """
        # disconnect the current layer
        if None != self._active_layer_:
            self._disconnect_signal_layerModified_(self._active_layer_)

        #
        self._update_current_layer_()

        if self._active_layer_ is not None:
            #
            if self._dlg_.isChecked():
                qgis_layer_tools.commit_changes_and_refresh(self._active_layer_, self._iface_, QSettings())
                self._connect_signal_layerModified_(self._active_layer_)
                #
                qgis_log_tools.logMessageINFO("Change Layer: self.currentLayer.name()=" + self._active_layer_.name())
        else:
            qgis_log_tools.logMessageINFO("No layer selected (for ITP)")