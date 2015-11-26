__author__ = 'latty'

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry

import psycopg2
import psycopg2.extras

import imt_tools
import trafipolluImp_Tools_Symuvia as tpi_TS

import tp_configparser as tp_config


# creation de l'objet logger qui va nous servir a ecrire dans les logs
from imt_tools import init_logger

logger = init_logger(__name__)


class trafipolluImp_SQL(object):
    """

    """

    def __init__(self, **kwargs):
        """

        """
        iface = kwargs['iface']
        self._map_canvas = iface.mapCanvas()
        #
        self._dict_sql_methods = {
            'update_def_zone_test': self._update_tables_from_qgis,
            'update_table_edges_from_qgis': self._update_tables_from_qgis,
            'update_tables_from_def_zone_test': self._update_tables_from_qgis,
            #
            'request_detecting_roundabouts_from_qgis': self._request_sql,
            'dump_informations_from_edges': self._request_sql,
            'dump_sides_from_edges': self._request_sql,
            'dump_informations_from_nodes': self._request_sql,
            'dump_informations_from_lane_interconnexion': self._request_sql
        }

        self._dict_params_server = {}
        self._init_from_default_values()
        if 'ConfigParser' in kwargs:
            self._init_from_configs(kwargs['ConfigParser'])

        self.connection = None
        self.cursor = None
        self.b_connection_to_postgres_server = False

        self.connect_sql_server()

    def __del__(self):
        """

        :return:
        """
        self.disconnect_sql_server()

    def _init_from_default_values(self):
        """

        :return:
        """
        self._dict_params_server = {
            'LOCAL': {
                'host': "localhost",
                'port': "5433",
                'user': "postgres",
                'password': "postgres",
                'connect_timeout': 2,
            },
            'IGN': {
                'host': "172.16.3.50",
                'port': "5432",
                'user': "streetgen",
                'password': "streetgen",
                'connect_timeout': 2,
            },
        }

    def _init_from_configs(self, configparser):
        """

        :param configparser:
        :return:

        """
        # LOCAL
        if configparser.has_section('sql_postgres_server_local'):
            self._dict_params_server['LOCAL'] = tp_config.get_dict_with_configs(
                configparser,
                'sql_postgres_server_local',
                self._dict_params_server['LOCAL']
            )
            #
            logger.info(u"self._dict_params_server['LOCAL']: {0:s}".format(self._dict_params_server['LOCAL']))
        # IGN
        if configparser.has_section('sql_postgres_server_ign'):
            self._dict_params_server['IGN'] = tp_config.get_dict_with_configs(
                configparser,
                'sql_postgres_server_local',
                self._dict_params_server['IGN']
            )
            #
            logger.info(u"self._dict_params_server['IGN']: {0:s}".format(self._dict_params_server['IGN']))

    def disconnect_sql_server(self):
        """

        :return:
        """
        if self.b_connection_to_postgres_server:
            self.cursor.close()
            self.connection.close()

    def connect_sql_server(self):
        """

        :return:
        """
        #
        for name_server in self._dict_params_server:
            try:
                self.connection = psycopg2.connect(
                    dbname="street_gen_3",
                    database="bdtopo_topological",
                    **self._dict_params_server[name_server]
                )
            except Exception, e:
                logger.fatal('PostGres : problem de connexion -> %s' % e)
            else:
                try:
                    # self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
                    self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                except Exception, e:
                    logger.fatal('PostGres : problem pour recuperer un cursor -> %s' % e)
                else:
                    logger.info('PostGres: connected with %s server' % name_server)
                    self.b_connection_to_postgres_server = True
                    break
        return self.b_connection_to_postgres_server

    def _update_tables_from_qgis(self, *args, **kwargs):
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
                logger.info("[SQL] - try to commit ...")
                connection.commit()
            except:
                pass
            else:
                return True

    def build_sql_parameters_with_map_extent(self):
        """

        :return:
        """

        mapCanvas = self._map_canvas
        mapCanvas_extent = mapCanvas.extent()
        # get the list points from the current extent (from QGIS MapCanvas)
        list_points_from_mapcanvas = imt_tools.construct_listpoints_from_extent(mapCanvas_extent)

        # url: http://qgis.org/api/classQgsMapCanvas.html#af0ffae7b5e5ec8b29764773fa6a74d58
        extent_src_crs = mapCanvas.mapSettings().destinationCrs()
        # url: http://qgis.org/api/classQgsCoordinateReferenceSystem.html#a3cb64f24049d50fbacffd1eece5125ee
        # srid of translated lambert 93 to match laser referential
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

        logger.info("* list_points_from_mapcanvas: %s", list_points_from_mapcanvas)
        logger.info("* gPolygonWkt: %s", gPolylineWkt)
        logger.info("* extent_postgisSrid: %s", extent_postgisSrid)
        logger.info("extent_src_crs.postgisSrid: %s", extent_src_crs.postgisSrid())

        return dict_parameters

    def build_sql_parameters_with_map_extent_for_roundabouts(self):
        """

        :return:
        """

        mapCanvas = self._map_canvas
        mapCanvas_extent = mapCanvas.extent()
        # get the list points from the current extent (from QGIS MapCanvas)
        list_points_from_mapcanvas = imt_tools.construct_listpoints_from_extent(mapCanvas_extent)

        # url: http://qgis.org/api/classQgsMapCanvas.html#af0ffae7b5e5ec8b29764773fa6a74d58
        extent_src_crs = mapCanvas.mapSettings().destinationCrs()
        # url: http://qgis.org/api/classQgsCoordinateReferenceSystem.html#a3cb64f24049d50fbacffd1eece5125ee
        # srid of translated lambert 93 to match laser referential
        extent_postgisSrid = 932011
        extent_dst_crs = QgsCoordinateReferenceSystem(extent_postgisSrid, QgsCoordinateReferenceSystem.PostgisCrsId)
        # url: http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/crs.html
        xform = QgsCoordinateTransform(extent_src_crs, extent_dst_crs)
        #
        list_points = [xform.transform(point) for point in list_points_from_mapcanvas]

        # list of lists of points
        gPolyline = QgsGeometry.fromPolygon([list_points])
        gPolylineWkt = gPolyline.exportToWkt()

        dict_parameters = {
            'gPolylineWkt': gPolylineWkt,
            'extent_postgisSrid': extent_postgisSrid
        }

        logger.info("* list_points_from_mapcanvas: %s", list_points_from_mapcanvas)
        logger.info("* gPolygonWkt: %s", gPolylineWkt)
        logger.info("* extent_postgisSrid: %s", extent_postgisSrid)
        logger.info("extent_src_crs.postgisSrid: %s", extent_src_crs.postgisSrid())

        return dict_parameters

    @staticmethod
    def build_sql_parameters_with_update_def_zone_test(
            b_update_def_zone_test_with_convex_hull_on_symuvia_network=False,
            **kwargs
    ):
        """

        :return:

        """

        gPolygonWkt = ''

        if b_update_def_zone_test_with_convex_hull_on_symuvia_network:
            shp_convex_hull, shp_list_extremites = tpi_TS.extract_convexhull_from_symuvia_network(**kwargs)
            gPolygonWkt = shp_convex_hull.wkt

        if gPolygonWkt == '':
            # Convex hull du reseau symuvia '/home/latty/__DEV__/__Ifsttar__/Envoi_IGN_2015_07/reseau_paris6_v31.xml'
            gPolygonWkt = 'POLYGON ((650701.858831 6860988.892569, 650685.579302 6860989.63957, 650637.589042 6861000.671025, 650625.9989689999 6861022.21112, 650475.062469 6861507.425974, 650919.609638 6862039.011138, 650988.736866 6862060.741522, 651337.303769 6861890.548595, 651383.122202 6861735.047361, 651396.56811 6861476.753853, 651404.1191219999 6861230.871522, 651403.524419 6861226.192165, 651019.06407 6861047.190387, 650836.022246 6861012.096856, 650701.858831 6860988.892569))'

        gPolygonSRID = 2154  # SRID du Lambert93

        logger.info('################ gPolygonWkt: ', gPolygonWkt)

        dict_parameters = {
            'gPolygonWkt': gPolygonWkt,
            'gPolygonSRID': gPolygonSRID
        }

        return dict_parameters

    def execute_sql_commands(self, sql_file, id_sql_method):
        """

        :return:
        """
        if not self.b_connection_to_postgres_server:
            self.connect_sql_server()

        if self.b_connection_to_postgres_server:

            dict_parameters = {}
            if id_sql_method == 'update_table_edges_from_qgis':
                dict_parameters = self.build_sql_parameters_with_map_extent()
            elif id_sql_method == 'request_detecting_roundabouts_from_qgis':
                dict_parameters = self.build_sql_parameters_with_map_extent_for_roundabouts()
            elif id_sql_method == 'update_def_zone_test':
                dict_parameters = self.build_sql_parameters_with_update_def_zone_test()

            sql_method = self._dict_sql_methods[id_sql_method]

            # all SQL commands (split on ';')
            sqlCommands = sql_file.split(';')

            list_results = []

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
                        self.cursor.execute(command, dict_parameters)
                        results_sql_request = sql_method(connection=self.connection, cursor=self.cursor)
                        # logger.info('type(results_sql_request): %s' % type(results_sql_request))
                        list_results.append(results_sql_request)
                except psycopg2.OperationalError, msg:
                    logger.warning("Command skipped: %s", msg)
                    # #
            return list_results

    def _request_sql(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:

        """
        try:
            cursor = kwargs['cursor']
        except:
            pass
        else:
            try:
                logger.info("[SQL] - try to cursor.fetchall ...")
                objects_from_sql_request = cursor.fetchall()
            except Exception, e:
                logger.fatal('Exception: %s' % e)
            else:
                return objects_from_sql_request