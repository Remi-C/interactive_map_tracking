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

from PyQt4.QtCore import QObject, SIGNAL, QUrl
from PyQt4.QtCore import pyqtSignal, pyqtSlot, Qt
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPoint, QGis
from qgis._gui import QgsRubberBand, QgsVertexMarker
import qgis_log_tools
import qgis_mapcanvas_tools


class ITP_WebView_iTowns(QObject):
    """
    """

    mapMoved = pyqtSignal('double', 'double', 'double', name='mapMoved')

    def __init__(
            self,
            qgis_iface,
            qt_dlg,
            qt_webview,
            url="http://www.itowns.fr/api/QT/testAPI.html",
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
        self.url = url
        self.qurl = QUrl(self.url)
        self.qurl.setUserInfo( "itowns:stereo" )
        #
        # self.webpos = WebPos()
        self.e = 0
        self.n = 0
        self.h = 0
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
        # self.position_geometry = QgsRubberBand(self.iface.mapCanvas(), QGis.Point)
        self.position_geometry = QgsVertexMarker(self.iface.mapCanvas())
        #
        self.bSignalForExtentsChangedConnected = False
        self.bSignalForExtentsChangedConnectedAndRenderCompleteConnected = False


    def connect_moveMap(self):
        """

        """
        self.mapMoved.connect(self.onMapMoved)

    # get a move command from ITowns (JS -> Python/Qt)
    @pyqtSlot('double', 'double', 'double')
    def onMapMoved(self, e,  n, h):
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

    def update_icon_position(self, **keys):
        """
        Add a icon on Qgis Map to localize the current position in iTowns
        Now it's just a position information (no orientation)

        """
        qgis_log_tools.logMessageINFO("")

        # self.position_geometry.reset()
        #
        # self.position_geometry = QgsRubberBand(self.iface.mapCanvas(), QGis.Point)
        # self.position_geometry = QgsVertexMarker(self.iface.mapCanvas())
        #
        # self.position_geometry.setWidth(width)
        # self.position_geometry.setIcon(icon_type)
        # self.position_geometry.addPoint(self.point_qgis)

        if 'qt_color' in keys:
            self.position_geometry.setColor(keys['qt_color'])
        if 'icon_type'in keys:
            self.position_geometry.setIconType(keys['icon_type'])
        if 'icon_size' in keys:
            self.position_geometry.setIconSize(keys['icon_size'])
        if 'pen_width' in keys:
            self.position_geometry.setPenWidth(keys['pen_width'])
        #
        if keys.setdefault('update_position', True):
            self.position_geometry.setCenter(self.point_qgis)

        qgis_log_tools.logMessageINFO("qt_color:" + str(keys['qt_color']))

    # synch the map position from iTowns to QGIS
    def moveMap_iTowns_to_QGIS(self):
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

    # send a move command to ITowns (Python/Qt -> JS)
    def moveMap_iTowns(self, e, n, h):
        """
        :param frame:
        :param e:
        :param n:
        :param h:
        """
        #
        self.synch_QGIS_iTowns_finish = False
        #
        moveMapJS = "itowns.setPanoramicPosition(" \
                    "{" + \
                    "x:" + str(e) + \
                    ",y:" + str(n) + \
                    ",z:" + str(h) + \
                    "});  // Set position in lambert93 (easting, h, northing)"
        #
        self.frame.evaluateJavaScript(moveMapJS)
        # TODO: need a event to know when iTowns state is on : 'render complete'
        self.synch_QGIS_iTowns_finish = True
        #
        qgis_log_tools.logMessageINFO("-> moveMapJS: " + moveMapJS)

    # Comment effectuer une surcharge de fonctions (ou polymorphisme paramétrique) ?
    # url: http://python.developpez.com/faq/?page=Les-fonctions
    def moveMap_QGIS_to_iTowns(self, **keys):
        #
        qgis_log_tools.logMessageINFO("")
        #
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
        #
        # qgis_mapcanvas_tools.refreshMapCanvas(self.iface)

    def load(self):
        """
        """
        #
        qgis_log_tools.logMessageINFO("")
        #
        self.webview.load(self.qurl)
        QObject.connect(self.webview, SIGNAL("loadFinished (bool)"), self.loadFinished)
        #
        self.connectSignalForExtentsChanged()

    def loadFinished(self, ok):
        """
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
            self.connect_moveMap()
            #
            try:
                self.moveMap_QGIS_to_iTowns(mapCanvas=self.iface.mapCanvas())
            except:
                qgis_log_tools.logMessageWARNING("EXCEPTION: \
                self.moveMap(mapCanvas=mapCanvas)")
        else:
            qgis_log_tools.logMessageINFO("## WebView : FAILED TO LOAD from " + str(self.url))

    def update_size_dlg_from_frame(self, dlg, frame, margin_width=60):
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
        #
        qgis_log_tools.logMessageINFO("self.synch_QGIS_iTowns_finish: " +
                                      str(self.synch_QGIS_iTowns_finish))
        qgis_log_tools.logMessageINFO("self.synch_iTowns_QGIS_finish: " +
                                      str(self.synch_iTowns_QGIS_finish))
        #
        if self.synch_iTowns_QGIS_finish:
            try:
                self.update_icon_position(qt_color=Qt.blue, icon_size=16, pen_width=8)
                self.moveMap_QGIS_to_iTowns(mapCanvas=mapCanvas)
            except:
                qgis_log_tools.logMessageWARNING("EXCEPTION: \
                self.moveMap(mapCanvas=mapCanvas)")
        else:
            self.update_icon_position(qt_color=Qt.red, icon_size=16, pen_width=8)


        if not self.bSignalForExtentsChangedConnectedAndRenderCompleteConnected:
            QObject.connect(
                mapCanvas,
                SIGNAL("renderComplete(QPainter*)"),
                self.canvasExtentsChangedAndRenderComplete)
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
        if not self.synch_QGIS_iTowns_finish:
            self.synch_QGIS_iTowns_finish = True
