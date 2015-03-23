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
from qgis._gui import QgsRubberBand
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
        self.point_QGIS = QgsPoint()
        #
        self.synch_iTowns_QGIS = True
        self.synch_QGIS_iTowns = True
        #
        self.synch_QGIS_iTowns_finish = True
        #
        self.position_geometry = QgsRubberBand(self.iface.mapCanvas(), QGis.Point)

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
            self.moveMap_QGIS()
        #
        qgis_log_tools.logMessageINFO("Position changed, do something with new coord: " +
                                      str(e) + ", " + str(n) + ", " + str(h))

    def update_icon_position(self, width=4, qt_color=Qt.blue, icon_type=QgsRubberBand.ICON_CIRCLE):
        """
        Add a circle on Qgis Map to localize the current position in iTowns
        Now it's just a position information (no orientation)

        :param width:
        :param qt_color:
        :param icon_type:

        """
        self.position_geometry.reset()
        #
        self.position_geometry = QgsRubberBand(self.iface.mapCanvas(), QGis.Point)
        #
        self.position_geometry.setWidth(width)
        self.position_geometry.setIcon(icon_type)
        self.position_geometry.setIconSize(width)
        self.position_geometry.setColor(qt_color)
        #
        self.position_geometry.addPoint(self.point_qgis)

    # synch the map position from iTowns to QGIS
    def moveMap_QGIS(self):
        #
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
        if self.synch_QGIS_iTowns:
            self.synch_QGIS_iTowns_finish = False
            #
            mapCanvas.setCenter(self.point_qgis)
            #
            self.update_icon_position(8, Qt.red)
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

        moveMapJS = "itowns.setPanoramicPosition(" \
                    "{" + \
                    "x:" + str(e) + \
                    ",y:" + str(n) + \
                    ",z:" + str(h) + \
                    "});  // Set position in lambert93 (easting, h, northing)"
        #
        self.frame.evaluateJavaScript(moveMapJS)
        #
        qgis_log_tools.logMessageINFO("-> moveMapJS: " + moveMapJS)

    def moveMap(self,
                qgis_point_coords=QgsPoint(),
                qgis_point_crs=QgsCoordinateReferenceSystem("IGNF:LAMB93"),
                z=35.0):
        #
        qgis_log_tools.logMessageINFO("")
        #
        src_crs = qgis_point_crs
        dst_crs = self.itown_crs
        xform = QgsCoordinateTransform(src_crs, dst_crs)
        itowns_point = xform.transform(qgis_point_coords)
        #
        self.moveMap_iTowns(itowns_point.x(), z, itowns_point.y())

        self.update_icon_position(8, Qt.blue)
        #
        qgis_mapcanvas_tools.refreshMapCanvas(self.iface)

    def load(self):
        """
        """
        #
        qgis_log_tools.logMessageINFO("")
        #
        self.webview.load(self.qurl)
        QObject.connect(self.webview, SIGNAL("loadFinished (bool)"), self.loadFinished)

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
            # self.frame.addToJavaScriptWindowObject("webpos", self.webpos)
            self.frame.addToJavaScriptWindowObject("webpos", self)
            #
            self.connect_moveMap()

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