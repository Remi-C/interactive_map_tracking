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

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPoint, QgsGeometry
import math

from PyQt4.QtCore import QObject, SIGNAL, QUrl, QTimer, QSizeF
from PyQt4.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt4.QtGui import QTextDocument
from qgis._gui import QgsRubberBand, QgsVertexMarker, QgsTextAnnotationItem

import qgis_log_tools
import qgis_mapcanvas_tools

# 'local' (to the class) namespace for this overloading
# now 'QgsPoint' it's our implementation
class QgsPoint(QgsPoint):
    """

    """
    # add a another way to init QgsPoint
    @staticmethod
    def fromParams(**keys):
        """
        urls:
        - http://stackoverflow.com/questions/1385759/should-init-call-the-parent-classs-init

        """
        x, y = 0, 0
        #
        if 'angle' in keys:
            #
            angle = keys['angle']
            radius = keys.setdefault('radius', 1.0)
            #
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius
        elif 'x' in keys or 'y' in keys:
            x = keys.setdefault('x', 0.0)
            y = keys.setdefault('y', 0.0)
        elif 'QgsPoint' in keys:
            qgspoint = keys.setdefault('QgsPoint', QgsPoint())
            #
            x = qgspoint.x()
            y = qgspoint.y()
        #
        return QgsPoint(x, y)

    # now, we can add usefuls operators for QgsPoint (vectoriel stuffs for example)
    def __add__(self, other):
        """
        urls:
        - https://docs.python.org/2/library/operator.html

        """
        return QgsPoint(self.x()+other.x(), self.y()+other.y())

class ITP_WebView_iTowns(QObject):
    """
    """

    signal_apiIsInisialized = pyqtSignal(name='apiIsInisialized')
    #
    signal_mapMoved = pyqtSignal('double', 'double', 'double', name='mapMoved')
    signal_zoomChanged = pyqtSignal('int', name='zoomChanged')
    signal_orientationChanged = pyqtSignal('double', 'double', name='orientationChanged')
    #
    signal_moveMap = pyqtSignal('double', 'double', 'double', name='moveMap')
    signal_addLayer = pyqtSignal('QString', name='addLayer')
    signal_measured = pyqtSignal('double', 'double', 'double', name='measured')

    def __init__(
            self,
            qgis_iface,
            qt_dlg,
            qt_webview,
            url="",
            crs_theDefinition="IGNF:LAMB93"):
        """
        """

        # Initialize the PunchingBag as a QObject
        QObject.__init__(self)

        #
        qgis_log_tools.logMessageINFO("")
        #
        self.iface = qgis_iface
        self.qt_dlg = qt_dlg
        self.webview = qt_webview
        #
        self.page = self.webview.page()
        self.frame = self.page.currentFrame()
        #
        self.qurl = QUrl(url)
        self.qurl.setUserInfo( "itowns:stereo" )
        #
        self.e = 0
        self.n = 0
        self.h = 0
        #
        self.fov = 0
        #
        self.yaw = 0
        self.pitch = 0
        #
        self.itown_crs = QgsCoordinateReferenceSystem(crs_theDefinition)
        #
        self.point_itowns = QgsPoint()
        self.point_qgis = QgsPoint()
        #
        self.synch_iTowns_QGIS = True
        self.synch_QGIS_iTowns = True
        #
        self.synch_QGIS_iTowns_finish = True
        self.synch_iTowns_QGIS_finish = True
        #
        self.aim_geometry = QgsRubberBand(self.iface.mapCanvas(), False)
        self.frustum_geometry = QgsRubberBand(self.iface.mapCanvas(), False)
        self.position_geometry = QgsVertexMarker(self.iface.mapCanvas())
        #
        self.bSignalForExtentsChangedConnected = False
        self.bSignalForExtentsChangedConnectedAndRenderCompleteConnected = False
        #
        self.bApiIsInisialized = False
        #
        self.qtimer_pointcloud = QTimer()
        self.qtimer_pointcloud.timeout.connect(self.cron_finish_init_api)
        #
        self.list_measures = []
        #
        self.measure_add_vertexmarker = True
        self.measure_add_annotation = True

    def connect_JS_to_QT(self):
        """

        """
        qgis_log_tools.logMessageINFO("")
        #
        self.signal_apiIsInisialized.connect(self.slot_apiIsInisialized)  # synch problem
        #
        self.slot_apiIsInisialized()    # launch 'manually' the initialisation slot

    def emit_moveMap(self, e, n, h):
        """

        :param e:
        :param n:
        :param h:
        """
        self.signal_moveMap.emit(e, n, h)
        qgis_log_tools.logMessageINFO("emit_moveMap")

    def emit_addLayer(self, layer_name):
        """

        :param layer_name:
        """

        addLayer_JS = 'addLayerNow("' + layer_name + ')'

        # self.signal_addLayer.emit(layer_name)     # problem
        self.frame.evaluateJavaScript(addLayer_JS)
        #
        # qgis_log_tools.logMessageINFO("emit_addLayer: " + layer_name)
        qgis_log_tools.logMessageINFO('self.frame.evaluateJavaScript(' + addLayer_JS + ')')

    def add_measure(self, e, n, h):
        """

        :param e:
        :param n:
        :param h:
        """
        mapCanvas = self.iface.mapCanvas()
        #
        src_crs = self.itown_crs
        dst_crs = mapCanvas.mapSettings().destinationCrs()
        #(
        xform = QgsCoordinateTransform(src_crs, dst_crs)
        #
        measure_itowns = QgsPoint(e, n)
        point_qgis = xform.transform(measure_itowns)
        #
        vm = None
        if self.measure_add_vertexmarker:
            vm = QgsVertexMarker(mapCanvas)
            self.vertexmarker_update_parameters(vm,
                                                qt_color=Qt.darkYellow,
                                                icon_size=8,
                                                pen_width=4,
                                                icon_type=QgsVertexMarker.ICON_BOX)
        #
        vm.setCenter(point_qgis)
        #
        textItem = None
        if self.measure_add_annotation:
            textItem = QgsTextAnnotationItem(mapCanvas)
            textItem.setMapPosition(point_qgis)
            textItem.setFrameSize(QSizeF(128, 60))
            # textItem.setDocument(QTextDocument('E:{0}\nN:{1}\nh:{2}'.format(e, n, h)))
            textItem.setDocument(QTextDocument('E: %f\nN: %f\nh: %f' % (e, n, h)))
            textItem.update()
        #
        self.list_measures.append({'vertexmarker': vm, 'iTowns_position': [e, n, h], 'textItem': textItem})
        #
        # print self.list_measures
        # print point_qgis

    @pyqtSlot('double', 'double', 'double')
    def slot_onMeasured(self, e, n, h):
        """

        :param e:
        :param n:
        :param h:
        """
        #
        self.add_measure(e, n, h)
        #
        qgis_log_tools.logMessageINFO("Measure 3D: " + str(e) + ", " + str(n) + ", " + str(h))

    # get a move command from ITowns (JS -> Python/Qt)
    @pyqtSlot('double', 'double', 'double')
    def slot_onMapMoved(self, e,  n, h):
        """
        :param e:
        :param n:
        :param h:
        """
        self.e = e
        self.n = n
        self.h = h
        #
        if self.synch_iTowns_QGIS:
            self.moveMap_iTowns_to_QGIS()
        #
        qgis_log_tools.logMessageINFO("Position changed, do something with new coord: " +
                                      str(e) + ", " + str(n) + ", " + str(h))

    # get a zoom changed from iTowns (JS -> Python/Qt)
    @pyqtSlot('int')
    def slot_onZoomChanged(self, fov):
        """

        :param fov:
        """
        qgis_log_tools.logMessageINFO("Zoom changed, do something with the new fov: " +
                                      str(fov))
        #
        self.fov = math.radians(fov)
        #
        self.update_2dfrustum(qt_color=Qt.darkYellow, icon_size=16, pen_width=8)

    # get an orienation changed from iTowns (JS -> Python/Qt)
    @pyqtSlot('double', 'double')
    def slot_onOrientationChanged(self, yaw, pitch):
        """

        :param yaw:
        :param pitch:
        """
        qgis_log_tools.logMessageINFO("Orienation changed, do something with the new orientation: " +
                                      str(yaw) + ", " + str(pitch))
        #
        self.yaw = yaw
        self.pitch = pitch
        #
        self.update_2dfrustum(qt_color=Qt.magenta, icon_size=16, pen_width=8)

    def cron_finish_init_api(self):
        """

        """
        #
        # self.emit_addLayer("pointCloud")
        self.frame.evaluateJavaScript('addLayerNow("pointCloud")')
        #
        self.frame.evaluateJavaScript('itowns.createSearchInput();')    # add search adress
        #
        self.emit_moveMap(651187, 0, 6861382)   # move to a localisation with points cloud
        #
        qgis_log_tools.logMessageINFO("")

    @pyqtSlot()
    def slot_apiIsInisialized(self):
        """

        """
        qgis_log_tools.logMessageINFO("api iTowns is initialized")
        #
        self.bApiIsInisialized = True
        #
        self.signal_mapMoved.connect(self.slot_onMapMoved)
        self.signal_zoomChanged.connect(self.slot_onZoomChanged)
        self.signal_orientationChanged.connect(self.slot_onOrientationChanged)
        self.signal_measured.connect(self.slot_onMeasured)
        #
        self.connectSignalForExtentsChanged()
        #
        try:
            self.moveMap_QGIS_to_iTowns(mapCanvas=self.iface.mapCanvas())
        except:
            qgis_log_tools.logMessageWARNING("EXCEPTION: \
            self.moveMap(mapCanvas=mapCanvas)")
        #
        # self.qtimer_pointcoud.start(1000)
        QTimer.singleShot(2000, self.cron_finish_init_api)
        #
        # self.emit_moveMap(651187, 0, 6861382)
        # self.emit_addLayer("pointCloud")

    def update_aim(self, mapCanvas, CS=100):
        """
        :param mapCanvas:

        """
        #
        self.aim_geometry.reset()
        self.aim_geometry = QgsRubberBand(self.iface.mapCanvas(), False)
        #
        aim_CS = mapCanvas.mapUnitsPerPixel()*CS
        aim_angle = math.pi/2.0 - self.yaw
        #
        aim_point = QgsPoint.fromParams(angle=aim_angle, radius=aim_CS) + self.point_qgis
        #
        aim_list_points = [self.point_qgis, aim_point]
        #
        self.aim_geometry.setToGeometry(QgsGeometry.fromPolyline(aim_list_points), None)
        #
        self.aim_geometry.setColor(Qt.green)
        self.aim_geometry.setWidth(5)
        #

    def update_frustum(self, mapCanvas, CS=100):
        """

        :param mapCanvas:

        """
        #
        aim_CS = mapCanvas.mapUnitsPerPixel()*CS
        #
        aim_angle = math.pi/2.0 - self.yaw
        #
        self.frustum_geometry.reset()
        self.frustum_geometry = QgsRubberBand(self.iface.mapCanvas(), False)
        #
        frustum_CS = aim_CS * 4
        frustum_angle = aim_angle
        frustum_hfov = self.fov * 0.5
        #
        frustum_point_0 = QgsPoint.fromParams(angle=frustum_angle-frustum_hfov, radius=frustum_CS) + self.point_qgis
        frustum_point_1 = QgsPoint.fromParams(angle=frustum_angle+frustum_hfov, radius=frustum_CS) + self.point_qgis
        #
        frustum_list_lines = [
            [self.point_qgis, frustum_point_0],
            [self.point_qgis, frustum_point_1]]
        #
        self.frustum_geometry.setToGeometry(QgsGeometry.fromMultiPolyline(frustum_list_lines), None)
        #
        self.frustum_geometry.setColor(Qt.darkCyan)
        self.frustum_geometry.setWidth(3)

    def vertexmarker_update_parameters(self, vm, **keys):
        """

        :param vm:
        :param keys:

        """
        if 'qt_color' in keys:
            vm.setColor(keys['qt_color'])
        if 'icon_type'in keys:
            vm.setIconType(keys['icon_type'])
        if 'icon_size' in keys:
            vm.setIconSize(keys['icon_size'])
        if 'pen_width' in keys:
            vm.setPenWidth(keys['pen_width'])

    def update_position(self, **keys):
        """
        Add a icon on Qgis Map to localize the current position in iTowns

        """
        self.vertexmarker_update_parameters(self.position_geometry, **keys)
        #
        if keys.setdefault('update_position', True):
            self.position_geometry.setCenter(self.point_qgis)

    def update_2dfrustum(self, **keys):
        """
        Add a icon on Qgis Map to represent the current:
            - position in iTowns
            - orientation of iTowns camera
            - zoom/fov of iTowns camera

        """
        qgis_log_tools.logMessageINFO("")

        mapCanvas = self.iface.mapCanvas()

        self.update_aim(mapCanvas)
        self.update_frustum(mapCanvas)
        self.update_position(**keys)
        #
        # qgis_log_tools.logMessageINFO("qt_color:" + str(keys['qt_color']))

    def moveMap_iTowns_to_QGIS(self):
        """
        Synchronize the map position from iTowns to QGIS

        """
        mapCanvas = self.iface.mapCanvas()
        mapcanvas_extent = mapCanvas.extent()
        #
        src_crs = self.itown_crs
        dst_crs = mapCanvas.mapSettings().destinationCrs()
        #(
        xform = QgsCoordinateTransform(src_crs, dst_crs)
        #
        self.point_itowns = QgsPoint(self.e, self.n)
        self.point_qgis = xform.transform(self.point_itowns)
        #
        self.synch_iTowns_QGIS_finish = False
        #
        mapCanvas.setCenter(self.point_qgis)
        #
        qgis_mapcanvas_tools.refreshMapCanvas(self.iface)
        #
        qgis_log_tools.logMessageINFO("point_qgis: " + str(self.point_qgis.x()) + ", " + str(self.point_qgis.y()))

    def moveMap_iTowns(self, e, n, h):
        """
        Send a move command to ITowns (Python/Qt -> JS)

        :param frame:
        :param e:
        :param n:
        :param h:
        """
        #
        self.synch_QGIS_iTowns_finish = False
        #
        self.emit_moveMap(e, n, h)
        # TODO: need a event to know when iTowns state is on : 'render complete'
        # self.synch_QGIS_iTowns_finish = True

    def moveMap_QGIS_to_iTowns(self, **keys):
        """
        Comment effectuer une surcharge de fonctions (ou polymorphisme paramétrique) ?
        url: http://python.developpez.com/faq/?page=Les-fonctions

        :param keys:
        """
        #
        qgis_log_tools.logMessageINFO("")
        #
        try:
            src_crs = None
            qgis_point_coords = None
            z = 35.0
            #
            if 'qgis_point_coords' in keys:
                qgis_point_coords = keys.setdefault('qgis_point_coords')
                src_crs = keys.setdefault('qgis_point_crs', QgsCoordinateReferenceSystem("IGNF:LAMB93"))
                z = keys.setdefault('z', 35.0)
            elif 'mapCanvas' in keys:
                mapCanvas = keys['mapCanvas']
                #
                mapcanvas_extent = mapCanvas.extent()
                qgis_point_coords = mapcanvas_extent.center()
                src_crs = mapCanvas.mapSettings().destinationCrs()
            else:
                pass

            dst_crs = self.itown_crs
            xform = QgsCoordinateTransform(src_crs, dst_crs)
            itowns_point = xform.transform(qgis_point_coords)

            self.moveMap_iTowns(itowns_point.x(), z, itowns_point.y())
        except:
            qgis_log_tools.logMessageINFO("EXCEPTION")

    def load(self):
        """

        """
        #
        qgis_log_tools.logMessageINFO("")
        #
        self.webview.load(self.qurl)
        #
        QObject.connect(self.webview, SIGNAL("loadFinished (bool)"), self.loadFinished)
        #
        qgis_log_tools.logMessageINFO("load url: " + str(self.qurl.toString()))

    def loadFinished(self, ok):
        """

        :param ok:
        """
        if ok:
            self.page = self.webview.page()
            self.frame = self.page.currentFrame()
            #
            qgis_log_tools.logMessageINFO("## WebView : OK")
            #
            width, height = self.update_size_dlg_from_frame(
                self.qt_dlg,
                self.frame)
            #
            qgis_log_tools.logMessageINFO("### width : " + str(width) + " - height : " + str(height))
            #
            self.frame.addToJavaScriptWindowObject("webpos", self)
            #
            self.connect_JS_to_QT()
        else:
            qgis_log_tools.logMessageINFO("## WebView : FAILED TO LOAD from " + str(self.qurl.toString()))

    def update_size_dlg_from_frame(self, dlg, frame, margin_width=60):
        """

        :param dlg:
        :param frame:
        :param margin_width:
        """
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

    def connectSignalForExtentsChanged(self):
        """ Connect the signal: 'Extent Changed' to the QGIS MapCanvas """
        #
        if not self.bSignalForExtentsChangedConnected:
            self.iface.mapCanvas().extentsChanged.connect(self.canvasExtentsChanged)
            self.bSignalForExtentsChangedConnected = True
            #
            qgis_log_tools.logMessageINFO("Connect SIGNAL on QGISMapCanvas")

    def disconnectSignalForExtentsChanged(self):
        """ Disconnect the signal: 'Canvas Extents Changed' of the QGIS MapCanvas """
        #
        if self.bSignalForExtentsChangedConnected:
            self.iface.mapCanvas().extentsChanged.disconnect(self.canvasExtentsChanged)
            self.bSignalForExtentsChangedConnected = False
            #
            qgis_log_tools.logMessageINFO("Disconnect SIGNAL on QGISMapCanvas")

    def canvasExtentsChanged(self):
        """

        """
        #
        mapCanvas = self.iface.mapCanvas()

        if mapCanvas:
            #
            qgis_log_tools.logMessageINFO("self.synch_QGIS_iTowns_finish: " +
                                          str(self.synch_QGIS_iTowns_finish))
            qgis_log_tools.logMessageINFO("self.synch_iTowns_QGIS_finish: " +
                                          str(self.synch_iTowns_QGIS_finish))
            #
            if self.synch_iTowns_QGIS_finish:
                try:
                    self.moveMap_QGIS_to_iTowns(mapCanvas=mapCanvas)
                    pass
                except:
                    qgis_log_tools.logMessageWARNING("EXCEPTION: \
                    self.moveMap(mapCanvas=mapCanvas)")

            if not self.bSignalForExtentsChangedConnectedAndRenderCompleteConnected:
                try:
                    QObject.connect(
                        mapCanvas,
                        SIGNAL("renderComplete(QPainter*)"),
                        self.canvasExtentsChangedAndRenderComplete)
                except:
                    qgis_log_tools.logMessageWARNING("EXCEPTION: \
                    QObject.connect(..., self.canvasExtentsChangedAndRenderComplete)")
                #
                self.bSignalForExtentsChangedConnectedAndRenderCompleteConnected = True

    def canvasExtentsChangedAndRenderComplete(self):
        #
        QObject.disconnect(
            self.iface.mapCanvas(),
            SIGNAL("renderComplete(QPainter*)"),
            self.canvasExtentsChangedAndRenderComplete)
        #
        self.bSignalForExtentsChangedConnectedAndRenderCompleteConnected = False
        #
        if not self.synch_iTowns_QGIS_finish:
            self.synch_iTowns_QGIS_finish = True
            #
            self.update_2dfrustum(qt_color=Qt.red, icon_size=16, pen_width=8)
        #
        if not self.synch_QGIS_iTowns_finish:
            self.synch_QGIS_iTowns_finish = True
            #
            self.update_2dfrustum(qt_color=Qt.blue, icon_size=16, pen_width=8)
