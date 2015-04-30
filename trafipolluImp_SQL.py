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
        #
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

    def __getstate__(self):
        """

        :return:
        """
        return self.saveState()

    def __setstate__(self, states):
        """

        :param states:
        :return:
        """
        self.pickle_states = states

    def saveState(self):
        """

        :return:
        """
        # note: normalement les objects numpy (array) et shapely (natif, wkb/t) sont 'dumpables'
        # et donc serialisables via Pickle !
        #
        # NUMPY test:
        # ----------
        # >>> import cPickle as pickle
        # >>> import numpy as np
        # >>> np_object = np.asarray([1, 2])
        # >>> pickle.dumps(np_object)
        # "cnumpy.core.multiarray\n_reconstruct\np1\n(cnumpy\nndarray\np2\n(I0\ntS'b'\ntRp3\n(I1\n(I2\ntcnumpy\ndtype\np4\n(S'i8'\nI0\nI1\ntRp5\n(I3\nS'<'\nNNNI-1\nI-1\nI0\ntbI00\nS'\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x02\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\ntb."
        # >>> str_dump_pickle = pickle.dumps(np_object)
        # >>> pickle.loads(str_dump_pickle)
        # array([1, 2])
        #
        # SHAPELY tests:
        # -------------
        # >>> import shapely.geometry as sp_geom
        # >>> import shapely.wkb as sp_wkb
        # >>> point = sp_geom.Point(0, 0)
        # >>> pickle.dumps(point)
        # "cshapely.geometry.point\nPoint\np1\n(tRp2\nS'\\x01\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\nb."
        # >>> pickle.dumps(point.wkb)
        # "S'\\x01\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\n."
        # >>> str_point_wkb = pickle.dumps(point.wkb)
        # >>> pickle.loads(str_point_wkb)
        # '\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        # >>> sp_wkb.loads(pickle.loads(str_point_wkb))
        # <shapely.geometry.point.Point object at 0x7fc00e1ace50>
        # >>> sp_wkb.loads(pickle.loads(str_point_wkb)).wkt
        # 'POINT (0 0)'

        dict_states_for_pickle = {
            'SQL': {
                'dict_edges': self.__dict_edges,
                'dict_lanes': self.__dict_lanes
            }
        }
        return dict_states_for_pickle

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