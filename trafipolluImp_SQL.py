__author__ = 'latty'

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry

import psycopg2
import psycopg2.extras

import imt_tools
import trafipolluImp_DUMP as tpi_DUMP
import trafipolluImp_EXPORT as tpi_EXPORT


class trafipolluImp_SQL(object):
    """

    """

    def __init__(self, iface):
        """

        """
        self.__mapCanvas = iface.mapCanvas()
        self.__dict_edges = {}  # key: id_edge  -   value: (topo) informations from SG3
        self.__dict_lanes = {}
        #
        self.__dict_sql_methods = {
            'update_table_edges_from_qgis': self._update_tables_from_qgis,
            'dump_informations_from_edges': self.__request_for_edges,
            'dump_sides_from_edges': self.__request_for_lanes
        }

        # TODO: TEST -> l'exporter ne sera pas dans cette classe (au final) !
        self.__exporter = tpi_EXPORT.trafipolluImp_EXPORT(self.__dict_edges, self.__dict_lanes)

    @staticmethod
    def _update_tables_from_qgis(*args, **kwargs):
        """

        :param cursor:
        :return:

        """
        try:
            connection = kwargs['connection']
        except:
            pass
        else:
            try:
                print "[SQL] - try to commit ..."
                connection.commit()
            except:
                pass

    def execute_SQL_commands(self, sqlFile, sql_choice_combobox):
        """

        :return:
        """
        mapCanvas = self.__mapCanvas
        mapCanvas_extent = mapCanvas.extent()
        # get the list points from the current extent (from QGIS MapCanvas)
        list_points_from_mapcanvas = imt_tools.construct_listpoints_from_extent(mapCanvas_extent)

        # url: http://qgis.org/api/classQgsMapCanvas.html#af0ffae7b5e5ec8b29764773fa6a74d58
        extent_src_crs = mapCanvas.mapSettings().destinationCrs()
        # url: http://qgis.org/api/classQgsCoordinateReferenceSystem.html#a3cb64f24049d50fbacffd1eece5125ee
        extent_postgisSrid = 932011
        extent_dst_crs = QgsCoordinateReferenceSystem(extent_postgisSrid, QgsCoordinateReferenceSystem.PostgisCrsId)
        # url: http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/crs.html
        xform = QgsCoordinateTransform(extent_src_crs, extent_dst_crs)
        #
        list_points = [xform.transform(point) for point in list_points_from_mapcanvas]

        # list of lists of points
        gPolyline = QgsGeometry.fromPolyline(list_points)
        gPolylineWkt = gPolyline.exportToWkt()

        dict_parameters = {
            'gPolylineWkt': gPolylineWkt,
            'extent_postgisSrid': extent_postgisSrid
        }

        # print "* list_points_from_mapcanvas: ", list_points_from_mapcanvas
        # print ""
        # print "* gPolygonWkt: ", gPolylineWkt
        # print ""
        # print "* extent_postgisSrid: ", extent_postgisSrid
        # print "* extent_src_crs.postgisSrid: ", extent_src_crs.postgisSrid()
        # print ""

        connection = psycopg2.connect(database="bdtopo_topological",
                                      dbname="street_gen_3",
                                      user="streetgen", password="streetgen",
                                      host="172.16.3.50")

        # cursor = connection.cursor()
        # cursor = connection.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # sql_filename = imt_tools.get_itemData(self.__dlg.combobox_sql_scripts)
        # fd = open(sql_filename)
        # sqlFile = fd.read()
        # fd.close()
        # sql_choice_combobox = imt_tools.get_itemText(self.__dlg.combobox_sql_scripts)
        # self.__dlg.plainTextEdit_sql_script.setPlainText(sqlFile)

        sql_method = self.__dict_sql_methods[sql_choice_combobox]

        # all SQL commands (split on ';')
        sqlCommands = sqlFile.split(';')

        # Execute every command from the input file
        for command in sqlCommands:
            # This will skip and report errors
            # For example, if the tables do not yet exist, this will skip over
            # the DROP TABLE commands
            try:
                # command = command.format(gPolylineWkt, extent_postgisSrid)
                # https://docs.python.org/2/library/string.html#string.Formatter
                # todo : look here for more advanced features on string formatter
                # command = command.format(**dict_parameters)

                if not command.isspace():
                    # url: http://initd.org/psycopg/docs/usage.html#query-parameters
                    # url: http://initd.org/psycopg/docs/advanced.html#adapting-new-types
                    cursor.execute(command, dict_parameters)
                    sql_method(connection=connection, cursor=cursor)
            except psycopg2.OperationalError, msg:
                print "Command skipped: ", msg
        cursor.close()
        connection.close()

    def __request_for_edges(self, **kwargs):
        """

        :param objects_from_sql_request:
        :return:

        """
        try:
            cursor = kwargs['cursor']
        except:
            pass
        else:
            try:
                print "[SQL] - try to cursor.fetchall ..."
                objects_from_sql_request = cursor.fetchall()
            except:
                pass
            else:
                tpi_DUMP.dump_for_edges(objects_from_sql_request, self.__dict_edges)

    def __request_for_lanes(self, **kwargs):
        """

        :param objects_from_sql_request:
        :param b_load_geom:
        :return:
        """
        try:
            cursor = kwargs['cursor']
        except:
            pass
        else:
            try:
                print "[SQL] - try to cursor.fetchall ..."
                objects_from_sql_request = cursor.fetchall()
            except:
                pass
            else:
                tpi_DUMP.dump_lanes(objects_from_sql_request, self.__dict_edges, self.__dict_lanes)

        # test export
        self.__exporter.export()