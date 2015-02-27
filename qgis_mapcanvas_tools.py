# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Interactive Map Tracking
                                 A QGIS plugin
 Tools for Interactive Map Tracking
                              -------------------
        begin                : 2015-02-10
        git sha              : $Format:%H$
        copyright            : (C) 2015 by IGN
        email                : lionel.atty@ign.fr
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

__author__ = 'latty'

from qgis.gui import QgsMessageBar
import qgis_log_tools

# constant value for epsilon
DEFAULT_SEGMENT_EPSILON = 1e-08


def refreshMapCanvas(iface):
    """Force QGIS to refresh the MapCanvas.
    We need to use a trick (infinitely small zoom) to force QGIS to refresh the map.
    Using the standard method 'refresh' from mapCanvas() don't work because the update is on DataBase side.

    :param iface: QGIS Interface given from to QGIS to IMT plugin
    :type iface: QgisInterface

    """
    qgis_log_tools.logMessageINFO("Try to refresh mapcanvas")

    mapRect = iface.mapCanvas().extent()
    iface.mapCanvas().zoomByFactor(1.0 + DEFAULT_SEGMENT_EPSILON, mapRect.center())


def refreshLayer(layer, iface):
    """Force QGIS to refresh/repaint the layer

    :param layer: Layer to refresh/repaint/rerender
    :type iface: QgsMapLayer

    """
    qgis_log_tools.logMessageINFO("Try to refresh: " + str(layer.name()))
    layer.triggerRepaint()
    iface.mapCanvas().refresh()

def find_layer_in_mapcanvas(_mapCanvas, _layername):
    """ Finding the index of an item given a list containing it in Python
    url : http://stackoverflow.com/questions/176918/finding-the-index-of-an-item-given-a-list-containing-it-in-python

    :param _mapCanvas:
    :type _mapCanvas:

    :param _layername:
    :type _layername:

    :rtype : QGIS layer
    """
    index_layer_searched = [iLayer for iLayer in range(_mapCanvas.layerCount()) if
                    _mapCanvas.layer(iLayer).name() == _layername]
    if not index_layer_searched:
        return None
    else:
        return _mapCanvas.layer(index_layer_searched[0])

def find_layer_in_mapcanvas(_mapCanvas, _layername):
    """ Finding the index of an item given a list containing it in Python
    url : http://stackoverflow.com/questions/176918/finding-the-index-of-an-item-given-a-list-containing-it-in-python

    :param _mapCanvas:
    :type _mapCanvas:

    :param _layername:
    :type _layername:

    :rtype : QGIS layer
    """
    index_layer_searched = [iLayer for iLayer in range(_mapCanvas.layerCount()) if _mapCanvas.layer(iLayer).name() == _layername]
    if not index_layer_searched:
        return None
    else:
        return _mapCanvas.layer(index_layer_searched[0])