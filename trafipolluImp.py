__author__ = 'atty'

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry

from signalsmanager import SignalsManager
import imt_tools
# from psycopg2.extras import NamedTupleConnection
from psycopg2.extras import DictCursor
from shapely.wkb import loads
import numpy as np
from collections import namedtuple
from itertools import groupby
import PyXB_on_Symuvia_reseau as reseau

class TrafiPolluImp(object):
    """

    """

    _lambdas_generate_id = {
        'left': lambda nb_lanes_by_2, position, even: nb_lanes_by_2 - int(position / 2),
        'right': lambda nb_lanes_by_2, position, even: nb_lanes_by_2 + int(position / 2) - even,
        'center': lambda nb_lanes_by_2, position, even: nb_lanes_by_2
    }

    def __init__(self, iface, dlg):
        """

        """
        self._iface = iface
        self._dlg = dlg
        self._mapCanvas = self._iface.mapCanvas()
        self._signals_manager = SignalsManager.instance()
        self.__dict_edges = {}  # key: id_edge  -   value: (topo) informations from SG3
        self.__dict_sides = {}
        self.__dict_grouped_lanes = {}

        self._dict_sql_methods = {
            'update_table_edges_from_qgis': self._update_table_edges_from_qgis,
            'dump_informations_from_edges': self._dump_informations_from_edges,
            'dump_sides_from_edges': self._dump_sides_from_edges
        }

        self.NAMEDTUPLE_LANESIDE_OUTCOMING = namedtuple(
            'NAMEDTUPLE_LANESIDE_OUTCOMING',
            [
                'lane_side',
                'oncoming'
            ]
        )

    def _init_signals_(self):
        """

        """
        self._signals_manager.add_clicked(self._dlg.execute_sql_commands, self.slot_execute_SQL_commands, "GUI")
        self._signals_manager.add_clicked(self._dlg.refreshSqlScriptList, self._slot_refreshSqlScriptList, "GUI")
        self._signals_manager.add(self._dlg.combobox_sql_scripts,
                                  "currentIndexChanged (int)",
                                  self._slot_currentIndexChanged_SQL,
                                  "GUI")

    def _enable_trafipollu_(self):
        """
        Connection with QGIS interface
        """
        pass

    def _disable_trafipollu_(self):
        """
        Disconnection with QGIS interface
        """
        pass

    def slot_execute_SQL_commands(self):
        """

        :return:
        """
        self.execute_SQL_commands()

    def load_geom_with_shapely_from_dict(self, dict):
        """

        :param dict:
        :return:
        """
        # ul: http://toblerity.org/shapely/manual.htmlhttp://toblerity.org/shapely/manual.html
        # url: http://gis.stackexchange.com/questions/89323/postgis-parse-geometry-wkb-with-ogr
        # url: https://docs.python.org/2/c-api/buffer.html
        for name_key in dict.keys():
            object = dict[name_key]
            if isinstance(object, buffer):
                dict[name_key] = loads(bytes(object))

    def _update_table_edges_from_qgis(self, *args, **kwargs):
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

    def _dump_informations_from_edges(self, *args, **kwargs):
        """

        :param objects_from_sql_request:
        :return:

        """
        try:
            cursor = kwargs['cursor']
            b_load_geom = kwargs.setdefault('b_load_geom', True)
        except:
            pass
        else:
            try:
                print "[SQL] - try to cursor.fetchall ..."
                objects_from_sql_request = cursor.fetchall()
            except:
                pass
            else:
                # self._dict_edges = {}
                # url: http://stackoverflow.com/questions/10252247/how-do-i-get-a-list-of-column-names-from-a-psycopg2-cursor
                # column_names = [desc[0] for desc in cursor.description]
                # namedtuple = imt_tools.create_named_tuple_from_names('DUMP_SQL_TRAFIPOLLU', column_names)
                for object_from_sql_request in objects_from_sql_request:
                    # url: http://www.dotnetperls.com/namedtuple
                    # tuple_trafipollu = namedtuple._make(tuple_from_sql_request)
                    # self._dict_edges.update({tuple_trafipollu.edge_id: tuple_trafipollu})

                    edge_id = object_from_sql_request['edge_id']

                    dict_sql_request = object_from_sql_request.copy()

                    self.__dict_edges.update({edge_id: dict_sql_request})

                    #
                    if b_load_geom:
                        self.load_geom_with_shapely_from_dict(self.__dict_edges[edge_id])

                    dict_sql_request['amont'] = np.asarray(self.__dict_edges[edge_id]['point_amont'])
                    dict_sql_request['aval'] = np.asarray(self.__dict_edges[edge_id]['point_aval'])
                    dict_sql_request['amont_to_aval'] = dict_sql_request['aval'] - dict_sql_request['amont']
                    dict_sql_request['linez_geom'] = np.asarray(self.__dict_edges[edge_id]['linez_geom'])

                    # print 'self._dict_edges: ', self._dict_edges
                    #

    @staticmethod
    def _compute_direction_linestring(np_linestring):
        """

        :param linestring:
        :return:
        """
        amont = np_linestring[0]
        aval = np_linestring[-1]
        return amont - aval

    @staticmethod
    def _edges_is_same_orientation(edge0, edge1):
        """

        :param edge0:
        :param edge1:
        :return:
        """
        return edge0.dot(edge1) < 0

    def _dump_sides_from_edges(self, cursor, *args, **kwargs):
        """

        :param objects_from_sql_request:
        :param b_load_geom:
        :return:
        """
        try:
            cursor = cursor
            b_load_geom = kwargs.setdefault('b_load_geom', True)
        except:
            pass
        else:
            try:
                print "[SQL] - try to cursor.fetchall ..."
                objects_from_sql_request = cursor.fetchall()
            except:
                pass
            else:
                # self._dict_sides = {}
                # get sides informations for each 'edge'/'troncon'
                for object_from_sql_request in objects_from_sql_request:
                    id_edge = object_from_sql_request['edge_id']
                    lane_side = object_from_sql_request['lane_side']
                    #
                    nb_lanes = self.__dict_edges[id_edge]['lane_number']
                    self.__dict_sides.setdefault(id_edge,
                                                 {
                                                     'id_list': [None] * nb_lanes  # pre-allocate size for list
                                                 })
                    #
                    lane_center_axis = object_from_sql_request['lane_center_axis']
                    oncoming = False
                    if b_load_geom:
                        lane_center_axis = np.asarray(loads(bytes(lane_center_axis)))
                        # self.__dict_edges[id_edge]['lane_center_axis'] = np_points_internes     # TODO: chaque voie a la meme structure d'axe (que le troncon) !
                        self.__dict_sides[id_edge].setdefault('lane_center_axis', []).append(lane_center_axis)
                        oncoming = not self._edges_is_same_orientation(
                            self.__dict_edges[id_edge]['amont_to_aval'],
                            self._compute_direction_linestring(lane_center_axis)
                        )
                    # update list sides for (grouping)
                    position = object_from_sql_request['lane_position']
                    lambda_generate_id = self._lambdas_generate_id[lane_side]
                    nb_lanes_by_2 = (nb_lanes / 2)
                    even = bool(1 - nb_lanes % 2)
                    id_in_list = lambda_generate_id(nb_lanes_by_2, position, even)
                    # print 'position: ', position
                    # print 'id: ', id
                    self.__dict_sides[id_edge]['id_list'][id_in_list] = self.NAMEDTUPLE_LANESIDE_OUTCOMING(lane_side,
                                                                                                           oncoming)
                print "_dict_sides:", self.__dict_sides

                # create the dict: __dict_grouped_lanes
                # contain : for each edge_id list of lanes in same direction
                map(lambda x, y: self.__dict_grouped_lanes.__setitem__(x, {'grouped_lanes': y}),
                    self.__dict_sides,
                    [
                        [sum(1 for i in g) for k, g in
                         groupby(self.__dict_sides[id_edge]['id_list'], lambda x: x.oncoming)]
                        for id_edge in self.__dict_sides
                    ])
                print "self._dict_grouped_lanes:", self.__dict_grouped_lanes

                # update dict_edges with lanes grouped informations
                # map(lambda x, y: self.__dict_edges.__setitem__(y,
                # dict(self.__dict_edges[y],
                # **self.__dict_grouped_lanes[y])),
                #     self.__dict_edges,
                #     self.__dict_grouped_lanes
                # )
                for edge_id in self.__dict_grouped_lanes:
                    self.__dict_edges[edge_id].update(self.__dict_grouped_lanes[edge_id])
                print "self._dict_edges: ", self.__dict_edges

        # test export
        self.export_sg3_to_symuvia()

    def _build_list_lanes(self, edge_id):
        """

        :param edge_id:
        :return:
        """
        list_directions = []
        # try:
        edge_sg3 = self.__dict_edges[edge_id]
        sides_edge_sg3 = self.__dict_sides[edge_id]
        # except:
        pass
        # else:
        nb_lanes = edge_sg3['lane_number']
        nb_lanes_by_2 = int(nb_lanes / 2)
        even = not (nb_lanes % 2)
        #
        list_directions = [False] * nb_lanes
        #
        print ''

        def update_list_sides(name_sides, lambda_for_id):
            """

            :param list_sides:
            :param lambda_for_id:

            """
            for side_infos in sides_edge_sg3[name_sides]:
                id = lambda_for_id(nb_lanes_by_2, side_infos[0], even)
                list_directions[id] = (name_sides, side_infos[0], side_infos[2])
                # print "side_infos: ", side_infos
                # print 'id: ', id

        if nb_lanes > 1:
            update_list_sides('left', self._lambdas_generate_id['left'])
            update_list_sides('right', self._lambdas_generate_id['right'])
        if not bool(even):
            update_list_sides('center', self._lambdas_generate_id['center'])
        return list_directions

    def _build_SYMUVIA_troncons_from_id(self, edge_id):
        """

        :param edge_id:
        :return:
        """
        try:
            edge_sg3 = self.__dict_edges[edge_id]
            side_edge_sg3 = self.__dict_sides[edge_id]
        except:
            pass
        else:
            # first : separate lanes to have mono-directionals lanes
            nb_lanes = edge_sg3['lane_number']


    def execute_SQL_commands(self, b_load_geom=True):
        """

        :return:
        """
        mapCanvas = self._mapCanvas
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
            'extent_postgisSrid': extent_postgisSrid,
        }

        print "* list_points_from_mapcanvas: ", list_points_from_mapcanvas
        print ""
        print "* gPolygonWkt: ", gPolylineWkt
        print ""
        print "* extent_postgisSrid: ", extent_postgisSrid
        print "* extent_src_crs.postgisSrid: ", extent_src_crs.postgisSrid()
        print ""

        import psycopg2

        connection = psycopg2.connect(database="bdtopo_topological",
                                      dbname="street_gen_3",
                                      user="streetgen", password="streetgen",
                                      host="172.16.3.50")

        # cursor = connection.cursor()
        # cursor = connection.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

        sql_filename = imt_tools.get_itemData(self._dlg.combobox_sql_scripts)
        fd = open(sql_filename)
        sqlFile = fd.read()
        fd.close()

        sql_choice_combobox = imt_tools.get_itemText(self._dlg.combobox_sql_scripts)
        sql_method = self._dict_sql_methods[sql_choice_combobox]

        self._dlg.plainTextEdit_sql_script.setPlainText(sqlFile)

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

    def _slot_refreshSqlScriptList(self):
        """

        """

        self._dlg.combobox_sql_scripts.clear()

        import os

        path = os.path.normcase(os.path.dirname(__file__))
        files = os.listdir(path)

        [
            self._dlg.combobox_sql_scripts.addItem(os.path.basename(i)[:-4], path + '/' + i)
            for i in files if i.endswith('.sql')
        ]

    def _slot_currentIndexChanged_SQL(self, id_index):
        """

        :param id_index:
        """
        sqlFile = ""
        fd = None
        try:
            fd = open(imt_tools.get_itemData(self._dlg.combobox_sql_scripts))
            if fd:
                sqlFile = fd.read()
                fd.close()
        except:
            sqlFile = "Error ! Can't read the SQL file"

        self._dlg.plainTextEdit_sql_script.setPlainText(sqlFile)

    def convert_SQL_to_Python(self, str_sql):
        """

        :param str_sql:
        :return:
        """
        try:
            first_split = str.split('(')
            sql_type = first_split[0]
            sql_type = sql_type.replace(' ', '')

        except:
            pass

    def export_sg3_to_symuvia(self,
                              infilename="/home/latty/__DEV__/__REMI__/plugins/interactive_map_tracking/reseau_symuvia_minimal.xml",
                              outfilename="/home/latty/__DEV__/__REMI__/plugins/interactive_map_tracking/export_sg3_to_symuvia.xml"):
        """

        :param filename:
        :return:
        """
        xml = open(infilename).read()
        sym_ROOT = reseau.CreateFromDocument(xml)

        sym_ROOT.RESEAUX.RESEAU[0].TRONCONS.reset()
        sym_ROOT.RESEAUX.RESEAU[0].TRONCONS = self.export_TRONCONS()

        self.save_ROOT(sym_ROOT, outfilename)

    def save_ROOT(self, sym_ROOT, outfilename):
        """

        :return:
        """
        return self.save_SYMUVIA_Node("ROOT_SYMUBRUIT", sym_ROOT, outfilename)

    def save_SYMUVIA_Node(self, element_name, sym_node, outfilename):
        """

        :param sym_node:
        :param outfilename:
        :return:
        """
        f = open(outfilename, "w")
        f.write(sym_node.toxml('utf-8', element_name=element_name))
        f.close()

    def export_TRONCONS(self):
        """

        :return:

        """
        sym_TRONCONS = reseau.CTD_ANON_93()
        for edge_id in self.__dict_edges:
            sym_TRONCONS.append(self.export_TRONCON(edge_id))
        return sym_TRONCONS

    def export_TRONCON(self, edge_id):
        """

        :param edge_id:
        :return:
        """
        sg3_edge = self.__dict_edges[edge_id]

        list_troncons = []
        grouped_lanes = sg3_edge['grouped_lanes']
        print 'grouped_lanes: ', grouped_lanes
        cur_id_lane = 0
        for id_group_lane in grouped_lanes:
            nb_lanes = id_group_lane
            list_lane_center_axis = []
            for id_lane in range(cur_id_lane, cur_id_lane + nb_lanes, 1):
                lane_center_axis = self.__dict_sides[edge_id]['lane_center_axis'][id_lane]
                list_lane_center_axis.append(lane_center_axis)
            print "list_lane_center_axis:", list_lane_center_axis

        sym_TRONCON = reseau.typeTroncon()
        #
        sym_TRONCON.id = sg3_edge['ign_id']
        sym_TRONCON.extremite_amont = sg3_edge['amont']
        sym_TRONCON.extremite_aval = sg3_edge['aval']
        sym_TRONCON.nb_voie = sg3_edge['lane_number']
        sym_TRONCON.largeur_voie = sg3_edge['road_width'] / sym_TRONCON.nb_voie
        #
        sym_TRONCON.id_eltamont = -1
        sym_TRONCON.id_eltaval = -1
        list_troncons.append(sym_TRONCON)
        return sym_TRONCON

    def export_POINTS_INTERNES(self, edge_id):
        """

        :param edge_id:
        :return:
        """
        list_points_internes = []
        # update list_POINTS_INTERNES
        try:
            # points_internes = self.__dict_edges[edge_id]['points_internes']
            # print "point_amont: ", self.__dict_edges[edge_id]['amont']
            # print "point aval: ", self.__dict_edges[edge_id]['aval']
            # print "points_internes: ", points_internes
            # for point_interne in points_internes[1:-1]:
            # for point_interne in points_internes:
            # list_points_internes.append(reseau.CTD_ANON_162(coordonnees=[point_interne[0], point_interne[1]]))
            pass
        except:
            print "exception in export_POINTS_INTERNES"
        finally:
            points_internes = reseau.typePointsInternes()
            [points_internes.append(x) for x in list_points_internes]
            return points_internes
