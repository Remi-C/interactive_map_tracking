__author__ = 'atty'

import qgis_layer_tools
import qgis_log_tools
from PyQt4.QtCore import QSettings
from signalsmanager import SignalsManager


# super() fails with error: TypeError “argument 1 must be type, not classobj”
# url: http://stackoverflow.com/questions/1713038/super-fails-with-error-typeerror-argument-1-must-be-type-not-classobj
class AutoSaveImp(object):
    """

    """
    def __init__(self, iface, dlg):
        """

        """
        self.iface = iface
        self.dlg = dlg
        self.mapCanvas = self.iface.mapCanvas()
        self.signals_manager = SignalsManager.getInstance()
        self.currentLayer = None

    def init_signals(self):
        """

        """
        self.signals_manager.add_clicked(self.dlg, self.slot_clicked_checkbox_autosave, "GUI")
        #
        self.connect_signal_currentLayerChanged()

    def enable_autosave(self):
        """

        """
        self.connect_signal_currentLayerChanged()
        #
        self.slot_clicked_checkbox_autosave()

    def disable_autosave(self):
        """

        """
        self.disconnect_signal_currentLayerChanged()
        #
        if self.currentLayer is not None:
            self.disconnect_signal_layerModified(self.currentLayer)

    def slot_clicked_checkbox_autosave(self):
        """ Action when the checkbox 'Enable Auto-Save and Refresh' is clicked """
        #
        qgis_log_tools.logMessageINFO("Launch 'enable_autosave(...)' ...")
        #
        if self.dlg.isChecked():
            self.update_current_layer()
            #
            if self.currentLayer is not None:
                self.connect_signal_layerModified(self.currentLayer)
        else:
            if self.currentLayer is not None:
                self.disconnect_signal_layerModified(self.currentLayer)

    def update_current_layer(self):
        """

        :return:
        """
        return_value = False
        try:
            # filtre sur les layers
            # if qgis_layer_tools.filter_layer_for_imt(self.iface.activeLayer():
            if qgis_layer_tools.filter_layer_for_imt(self.iface.activeLayer(),
                                                     [qgis_layer_tools.filter_layer_vectorlayer]):  # for test
                #
                qgis_log_tools.logMessageINFO("Active layer: " + self.iface.activeLayer().name()
                                              + "is 'compatible' for Auto-Saving !"
                                              + "- [OK]")
                #
                self.currentLayer = self.iface.activeLayer()
                #
                return_value = True
            else:
                qgis_log_tools.logMessageWARNING("Active layer: " + self.iface.activeLayer().name()
                                                 + "is not 'compatible' for Auto-Saving ! (VectorLayer + PostGIS)"
                                                 + "- [FAILED]")
                #
                self.currentLayer = None
        except:
            qgis_log_tools.logMessageINFO("Exception here!")
        #
        return return_value

    def connect_signal_layerModified(self, layer):
        """ Connect the signal: "Layer Modified" to the layer given

        :param layer: QGIS layer
        :type layer: QgsMapLayer

        """
        if layer is not None:
            self.signals_manager.add(layer,
                                     "layerModified()",
                                     self.slot_layerModified,
                                     "QGIS")
            #
            qgis_log_tools.logMessageINFO("Connect SIGNAL on layer: " + layer.name())

    def disconnect_signal_layerModified(self, layer):
        """ Disconnect the signal: 'Layer Modified' of the layer given

        :param layer: QGIS Layer
        :type layer: QgsMapLayer

        """
        if layer is not None:
            self.signals_manager.disconnect(layer, "layerModified()")
            #
            qgis_log_tools.logMessageINFO("Disconnect SIGNAL on layer: " + layer.name())

    def slot_layerModified(self):
        """ Action when the signal: 'Layer Modified' from QGIS Layer (current) is emitted&captured
        We connect a new signal: 'RenderComplete' to perform operation after the QGIS rendering (deferred strategy)

        """
        #
        # if self.currentLayer is not None and self.mapCanvas is not None:
        #
        #
        self.signals_manager.add(
            self.mapCanvas,
            "renderComplete(QPainter*)",
            self.slot_renderComplete_layerModified
        )
        qgis_log_tools.logMessageINFO("Detect modification on layer:" + self.currentLayer.name())

    def slot_renderComplete_layerModified(self):
        """ Action when the signal: 'Render Complete' from QGIS Layer (current) is emitted&captured (after emitted&captured signal: 'Layer Modified') """
        #
        self.signals_manager.disconnect(self.mapCanvas, "renderComplete(QPainter*)")
        #
        qgis_layer_tools.commit_changes_and_refresh(self.currentLayer, self.iface, QSettings())

    def     connect_signal_currentLayerChanged(self):
        """ Connect the signal: 'Layer Changed' to the layer given """
        self.connect_signal_qgis(self.iface, "currentLayerChanged(QgsMapLayer*)", self.slot_currentLayerChanged)
        #
        qgis_log_tools.logMessageINFO("Connect SIGNAL on QGISInterface")

    def disconnect_signal_currentLayerChanged(self):
        """ Disconnect the signal: 'Current Layer Changed' of the QGIS Interface"""
        #
        self.signals_manager.disconnect(self.iface, "currentLayerChanged(QgsMapLayer*)")
        #
        qgis_log_tools.logMessageINFO("Disconnect SIGNAL on QGISInterface")

    def connect_signal_qgis(self, qgis_object, signal_signature, slot):
        """

        :param qgis_object:
        :param signal_signature:
        :param slot:

        """
        if qgis_object:
            self.signals_manager.add(qgis_object,
                                     signal_signature,
                                     slot,
                                     "QGIS")

    def slot_currentLayerChanged(self, layer):
        """ Action when the signal: 'Current Layer Changed' from QGIS MapCanvas is emitted&captured

        :param layer: QGIS layer -> current layer using by Interactive_Map_Tracking plugin
        :type layer: QgsMapLayer

        """
        # disconnect the current layer
        if None != self.currentLayer:
            self.disconnect_signal_layerModified(self.currentLayer)

        #
        self.update_current_layer()

        if self.currentLayer is not None:
            #
            if self.dlg.isChecked():
                qgis_layer_tools.commit_changes_and_refresh(self.currentLayer, self.iface, QSettings())
                self.connect_signal_layerModified(self.currentLayer)
                #
                qgis_log_tools.logMessageINFO("Change Layer: self.currentLayer.name()=" + self.currentLayer.name())
        else:
            qgis_log_tools.logMessageINFO("No layer selected (for ITP)")