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

import qgis_gui_tools
import qgis_mapcanvas_tools
import qgis_log_tools

from qgis.gui import QgsMessageBar


def commit_changes(layer, iface, s, bShowCommitError=True):
    """Try to commitChange (saving) a QGIS Layer.

    :param layer: QGIS layer to commit
    :type layer: QgsMapLayer

    :param iface: QGIS Interface given from QGIS to the plugin
    :type iface: QgisInterface

    :param s: Qt settings
    :type s: QSettings

    :param bShowCommitError: Option [default=True].
     If True: If error/exception show the commit error
    :type bShowCommitError: bool

    :return: Result of the commit
    :rtype: bool
    """

    result_commit = False

    # no layer selected (i.e. empty project)
    if layer is None:
        return False

    if layer.isEditable() and layer.isModified():
        # save the previous state for node tool editing
        qgis_gui_tools.push_state_tools_editing(iface, s)

        # QGIS python - identify and highlight features programatically
        # url: http://gis.stackexchange.com/questions/86817/qgis-python-identify-and-highlight-features-programatically
        # layerSelectedFeatures = layer.selectedFeatures()

        #
        try:
            qgis_log_tools.logMessageINFO(
                "Try to commitChanges the layer: " + layer.name())
            # send request to DB
            result_commit = layer.commitChanges()

        except Exception, e:
            qgis_log_tools.logMessageCRITICAL("Exception captured= ", e)
            #
            result_commit = False

        if result_commit:
            # restore state
            layer.startEditing()

            # restore the previous state for (node) tools editing
            qgis_gui_tools.pop_state_tools_editing(iface, s)

            # restore selected feature for the current (edit) layer
            # layer.setSelectedFeatures(layerSelectedFeatures)
        else:
            qgis_log_tools.logMessageCRITICAL(
                "Can't commitChanges the layer: " + layer.name())

            commit_error_string = layer.commitErrors()[2]
            qgis_log_tools.logMessageCRITICAL(">>> " + commit_error_string)

            if bShowCommitError:
                # url : http://www.tutorialspoint.com/python/python_strings.htm
                # +2 to skip ': ' prefix of commitError msg
                commitErrorStringShort = commit_error_string[
                    commit_error_string.rfind(":") + 2:]

                # fonctionne sans probleme car integree directement dans QGIS
                # (interne au mecanisme d'info/warning)
                iface.messageBar().pushMessage(
                    "IMT. ERROR : " + "\"" + commitErrorStringShort + "\"",
                    "",
                    QgsMessageBar.CRITICAL, 0)
    #
    return result_commit


def commit_changes_and_refresh(layer, iface, s):
    """Try to commitChange (saving) a QGIS Layer and refresh the QGIS MapCanvas (screen).

    :param layer: QGIS layer to commit
    :type layer: QgsMapLayer

    :param iface: QGIS Interface given from QGIS to the plugin
    :type iface: QgisInterface

    :param s: Qt settings
    :type s: QSettings

    :return: Result of the commit
    :rtype: bool
    """
    bResultCommit = commit_changes(layer, iface, s)
    if bResultCommit:
        qgis_mapcanvas_tools.refreshMapCanvas(iface)    # use a trick here
        # qgis_mapcanvas_tools.refreshLayer(layer, iface)   # don't work ...
        # but we don't know why :'(
    return bResultCommit


def filter_layer_postgis(
    layer,
    list_filters=[
        "PostgreSQL",
        "database",
        "PostGIS"
    ]
):
    """ Helper to decided if 'layer' is provided by PostGre with PostGIS extension.

        The storage type of this layer is PostGres with PostGIS extension ?
        * urls:
        - http://qgis.org/api/classQgsVectorDataProvider.html#a75e5f96947340c0630c223a20601c7e8
        - http://www.tutorialspoint.com/python/string_find.htm
        - http://stackoverflow.com/questions/1712227/how-to-get-the-size-of-a-list

        In QGIS Python console:
        >>> qgis.utils.iface.activeLayer().dataProvider().storageType()
        u'PostgreSQL database with PostGIS extension'

    :param layer: QGIS layer to commit
    :type layer: QgsMapLayer

    :param list_filters: List of strings. list_filters defined 'strings filters' needed to accept this layer.
    :type list_filters: list

    :return: Result of the filter
    :rtype: bool
    """
    result = False
    try:
        if not(None is layer):
            data_provider = layer.dataProvider()
            if not(None is data_provider):
                storageType = data_provider.storageType()
                index = 0
                len_list_filters = len(list_filters)
                bContinue = (index < len_list_filters) and (
                    storageType.find(list_filters[index]) != -1)
                while bContinue:
                    index += 1
                    bContinue = (index < len_list_filters) and (
                        storageType.find(list_filters[index]) != -1)
                result = (index == len_list_filters)
    except:
        qgis_log_tools.logMessageWARNING("Problem with layer: " + layer.name())
    #
    return result


def filter_layer_vectorlayer(layer, layertype=0):
    """ Helper to decided if 'layer' is a QGIS Vector Layer.

    url: http://qgis.org/api/2.6/classQgsMapLayer.html#adf3b0b576d7812c4359ece2142170308
    Enumerator:
        VectorLayer   (=0)
        RasterLayer
        PluginLayer


    :param layer: QGIS layer to commit
    :type layer: QgsMapLayer

    :param layertype: Integer defined type QGIS MapLayer searched (QGIs enum value from C++ API)
    :type layertype: int

    :return: Result of the filter
    :rtype: bool
    """
    return not(layer is None) and (layer.type() == layertype)


#
def filter_layer_for_imt(layer,
                         list_filters=[
                             filter_layer_vectorlayer,
                             filter_layer_postgis
                         ]
                         ):
    """ Helper to decided if 'layer' is acceptable for IMT (AutoSave&Refresh)
    i.e. 'layer' is a QGIS Vector Layer and 'layer' is provide by PostGres with PostGis extension

    :param layer: QGIS layer to commit
    :type layer: QgsMapLayer

    :return: Result of the filter
    :rtype: bool
    """
    for filter in list_filters:
        if not filter(layer):
            return False
    return True
    # return filter_layer_vectorlayer(layer) and filter_layer_postgis(layer)
    # return filter_layer_vectorlayer(layer)


def filter_layer_trackingposition_required_fields(
        layer,
        list_fields=["user_id", "w_time"]):
    """ Helper to decided if 'layer' has at least 2 fields :
    - 'user_id' [:text]
    - 'w_time' [:text]

    :param layer: QGIS layer to commit
    :type layer: QgsMapLayer

    :return: Result list of indices for fields given (in list fields)
    or return empty list if problem (don't found fields)
    :rtype: list[int]
    """
    try:
        fields = layer.dataProvider().fields()
        # get fields name from the layer
        field_names = [field.name() for field in fields]
        #
        list_id_fields = [
            field_names.index(name_field) for name_field in list_fields]
    except:
        return []
    return list_id_fields


def filter_layer_for_trackingposition(layer):
    """ Helper to decided if 'layer' is compatible for Tracking Position
    i.e. 'layer' is a QGIS Vector Layer and 'layer' has at least 2 fields : 'user_id' [:text] & 'w_time' [:text]

    :param layer: QGIS layer to commit
    :type layer: QgsMapLayer

    :return: Result of the filter
    :rtype: bool
    """
    return filter_layer_vectorlayer(layer) and filter_layer_trackingposition_required_fields(layer)
