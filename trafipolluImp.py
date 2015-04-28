__author__ = 'atty'

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry

from signalsmanager import SignalsManager
import imt_tools
from psycopg2.extras import DictCursor
from shapely.wkb import loads
from shapely.geometry import LineString, Point
import numpy as np
from collections import namedtuple
from itertools import groupby
import PyXB_on_Symuvia_reseau as reseau

###################################################
### ALIAS des classes de binding
### verifier les liens si problemes !
###################################################
CTD_SYMUVIA_TRONCONS = reseau.CTD_ANON_93
CTD_SYMUVIA_POINT_INTERNE = reseau.CTD_ANON_162
###################################################


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
        self.__dict_lanes = {}
        self.__dict_grouped_lanes = {}

        self._dict_sql_methods = {
            'update_table_edges_from_qgis': self._update_table_edges_from_qgis,
            'dump_informations_from_edges': self._dump_informations_from_edges,
            'dump_sides_from_edges': self._dump_lanes_from_edges
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
        self._signals_manager.add_clicked(self._dlg.refreshSqlScriptList, self.__slot_refreshSqlScriptList, "GUI")
        self._signals_manager.add(self._dlg.combobox_sql_scripts,
                                  "currentIndexChanged (int)",
                                  self.__slot_currentIndexChanged_SQL,
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
        return edge0.dot(edge1) > 0

    def _dump_lanes_from_edges(self, cursor, *args, **kwargs):
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
                    self.__dict_lanes.setdefault(id_edge,
                                                 {
                                                     'id_list': [None] * nb_lanes  # pre-allocate size for list
                                                 })
                    #
                    lane_center_axis = object_from_sql_request['lane_center_axis']
                    oncoming = False
                    if b_load_geom:
                        lane_center_axis = np.asarray(loads(bytes(lane_center_axis)))
                        self.__dict_lanes[id_edge].setdefault('lane_center_axis', []).append(lane_center_axis)
                        oncoming = self._edges_is_same_orientation(
                            self.__dict_edges[id_edge]['amont_to_aval'],
                            self._compute_direction_linestring(lane_center_axis)
                        )
                    # update list sides for (grouping)
                    position = object_from_sql_request['lane_position']
                    lambda_generate_id = self._lambdas_generate_id[lane_side]
                    nb_lanes_by_2 = (nb_lanes / 2)
                    even = not bool(nb_lanes % 2)
                    id_in_list = lambda_generate_id(nb_lanes_by_2, position, even)
                    self.__dict_lanes[id_edge]['id_list'][id_in_list] = self.NAMEDTUPLE_LANESIDE_OUTCOMING(lane_side,
                                                                                                           oncoming)
                    # print 'position: ', position
                    # print 'id: ', id
                # print "** _dict_sides:", self.__dict_sides

                # create the dict: __dict_grouped_lanes
                # contain : for each edge_id list of lanes in same direction
                map(lambda x, y: self.__dict_grouped_lanes.__setitem__(x, {'grouped_lanes': y}),
                    self.__dict_lanes,
                    [
                        [sum(1 for i in g) for k, g in
                         groupby(self.__dict_lanes[id_edge]['id_list'], lambda x: x.oncoming)]
                        for id_edge in self.__dict_lanes
                    ])
                # print "** self._dict_grouped_lanes:", self.__dict_grouped_lanes

                # update dict_edges with lanes grouped informations
                # map(lambda x, y: self.__dict_edges.__setitem__(y,
                # dict(self.__dict_edges[y],
                # **self.__dict_grouped_lanes[y])),
                #     self.__dict_edges,
                #     self.__dict_grouped_lanes
                # )
                for k, v in self.__dict_grouped_lanes.items():
                    self.__dict_edges[k].update(v)
                # print "** self._dict_edges: ", self.__dict_edges

        # test export
        self.export_sg3_to_symuvia()

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

        # print "* list_points_from_mapcanvas: ", list_points_from_mapcanvas
        # print ""
        # print "* gPolygonWkt: ", gPolylineWkt
        # print ""
        # print "* extent_postgisSrid: ", extent_postgisSrid
        # print "* extent_src_crs.postgisSrid: ", extent_src_crs.postgisSrid()
        # print ""

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

    def __slot_refreshSqlScriptList(self):
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

    def __slot_currentIndexChanged_SQL(self, id_index):
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
        sym_TRONCONS = CTD_SYMUVIA_TRONCONS()
        for edge_id in self.__dict_lanes:
            for sym_TRONCON in self.export_TRONCON(edge_id):
                sym_TRONCONS.append(sym_TRONCON)
        return sym_TRONCONS

    def export_TRONCON(self, edge_id):
        """

        :param edge_id:
        :return: [] : list of sym_TRONCON

        """
        list_troncons = []

        sg3_edge = self.__dict_edges[edge_id]

        # print "sg3_edge: ", sg3_edge
        try:
            grouped_lanes = sg3_edge['grouped_lanes']
        except:
            # Il y a des edge_sg3 sans voie(s) dans le reseau SG3 ... faudrait demander a Remi !
            # Peut etre des edges_sg3 aidant uniquement aux connexions/creation (de zones) d'intersections
            print ""
            print "!!! 'BUG' with edge id: ", edge_id, " - no 'group_lanes' found !!!"
            print ""
        else:
            if len(grouped_lanes) > 1:
                # on a plusieurs groupes de voies (dans des directions differentes) pour ce troncon
                cur_id_lane = 0
                for id_group_lane in grouped_lanes:
                    nb_lanes = id_group_lane
                    sym_TRONCON = self.init_TRONCON(sg3_edge)
                    if nb_lanes > 1:
                        # groupe de plusieurs voies dans la meme direction
                        self.build_TRONCON_lanes_in_groups(sym_TRONCON, edge_id, cur_id_lane, nb_lanes)
                    else:
                        # groupe d'une seule voie (pour une direction)
                        self.build_TRONCON_lane_in_groups(sym_TRONCON, edge_id, cur_id_lane, nb_lanes)
                    #
                    list_troncons.append(sym_TRONCON)
                    # next lanes group
                    cur_id_lane += nb_lanes
            else:
                # le troncon possede 1 groupe de voies mono-directionnelles
                nb_lanes = grouped_lanes[0]
                #
                sym_TRONCON = self.init_TRONCON(sg3_edge)
                self.build_TRONCON_lanes_in_one_group(sym_TRONCON, sg3_edge, nb_lanes)
                #
                list_troncons.append(sym_TRONCON)
        finally:
            return list_troncons

    def build_TRONCON_lanes_in_groups(self, sym_TRONCON, edge_id, cur_id_lane, nb_lanes):
        """
        1 Groupe de plusieurs voies (dans la meme direction) dans une serie de groupes (de voies) pour l'edge_sg3
        Pas encore finie, experimental car le cas n'est pas present dans le reseau (pas possible de tester directement
        cet algo).
        :return:
        """
        lanes_center_axis = []
        # transfert lane_center_axis for each lane in 2D
        list_1D_coefficients = []
        # on parcourt le groupe de 'voies' dans le meme sens
        for id_lane in range(cur_id_lane, cur_id_lane + nb_lanes, 1):
            # get the linestring of the current lane
            linestring = LineString(self.__dict_lanes[edge_id]['lane_center_axis'][id_lane])
            # project this linestring into 1D coefficients
            linestring_proj = [
                linestring.project(Point(point), normalized=True)
                for point in list(linestring.coords)
            ]
            # save the lane informations
            lane_center_axis = {
                'LineString': linestring,
                'LineString_Proj': linestring_proj
            }
            lanes_center_axis.append(lane_center_axis)
            # update the list of 1D coefficients
            list_1D_coefficients += linestring_proj

        ###########################
        # clean the list of 1D coefficients
        # remove duplicate values
        # url: http://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-in-python-whilst-preserving-order
        list_1D_coefficients = list(set(list_1D_coefficients))
        # sort the list of 1D coefficients
        list_1D_coefficients.sort()
        ###########################

        # Compute the troncon center axis
        # Methode: on utilise les coefficients 1D de chaque voie qui va composer ce troncon.
        # On retroprojete chaque coeffient (1D) sur l'ensemble des voies (2D) et on effectue la moyenne des positions
        # On recupere 'une sorte d'axe median' des voies (du meme groupe)
        #
        # coefficient de normalisation depend du nombre de voies qu'on utilise pour la moyenne
        norm_lanes_center_axis = 1.0 / len(lanes_center_axis)
        troncon_center_axis = []
        # pour chaque coefficient 1D
        for coef_point in list_1D_coefficients:
            # on calcule la moyenne des points sur les lanes pour ce coefficient
            point_for_troncon = Point(0, 0)
            # pour chaque lane
            for lane_center_axis in lanes_center_axis:
                # on recupere la geometrie
                linestring = lane_center_axis['LineString']
                # on projete le coefficient et on somme le point
                point_for_troncon += linestring.interpolate(coef_point)
            # on calcule la moyenne
            point_for_troncon *= norm_lanes_center_axis
            troncon_center_axis.append(point_for_troncon)
            #
            # print "point_for_troncon: ", point_for_troncon.wkt
            # print "list_lane_center_axis:", lanes_center_axis
            # print "list_1D_coefficients:", list_1D_coefficients

        # Comme la liste des coefficients 1D est triee,
        # on peut declarer le 1er et dernier point comme Amont/Aval
        sym_TRONCON.nb_voie = nb_lanes
        sym_TRONCON.POINTS_INTERNES = self.export_POINTS_INTERNES(troncon_center_axis[1:-1])
        sym_TRONCON.extremite_amont = troncon_center_axis[0]    # 1er point
        sym_TRONCON.extremite_aval = troncon_center_axis[-1]    # dernier point

    def build_TRONCON_lanes_in_one_group(self, sym_TRONCON, sg3_edge, nb_lanes):
        """
        Plusieurs voies (meme direction) dans 1 unique groupe pour une edge_sg3
        L'idee dans ce cas est d'utiliser les informations geometriques d'edge_sg3 (centre de l'axe de l'edge)
        Faut faire attention au clipping pour ne recuperer qu'a partir d'amont/aval du troncon correspondant
        :return:
        """
        sym_TRONCON.nb_voie = nb_lanes
        #
        edge_center_axis = LineString(sg3_edge['linez_geom'])
        # note : on pourrait recuperer le sens avec les attributs 'left' 'right' des lanes_sg3
        # ca eviterait le sort (sur 2 valeurs c'est pas ouf mais bon)
        list_amont_aval_proj = sorted(
            [
                edge_center_axis.project(Point(sg3_edge['amont'])),
                edge_center_axis.project(Point(sg3_edge['aval']))
            ]
        )
        # print "++ list_amont_aval_proj: ", list_amont_aval_proj
        # on recupere les coefficients 1D des amont/aval
        coef_amont, coef_aval = list_amont_aval_proj
        troncon_center_axis = []
        # liste des points formant l'axe de l'edge_sg3
        for point in list(edge_center_axis.coords):
            coef_point = edge_center_axis.project(Point(point))
            # clipping du point, pour etre sure d'etre amont et aval
            if coef_point >= coef_amont and coef_point <= coef_aval:
                troncon_center_axis.append(point)
        # print "++ troncon_center_axis: ", troncon_center_axis

        sym_TRONCON.POINTS_INTERNES = self.export_POINTS_INTERNES(troncon_center_axis)
        #
        sym_TRONCON.extremite_amont = sg3_edge['amont']
        sym_TRONCON.extremite_aval = sg3_edge['aval']

    def build_TRONCON_lane_in_groups(self, sym_TRONCON, edge_id, cur_id_lane, nb_lanes):
        """
        1 voie dans une serie de groupe.
        Cas le plus simple, on recupere les informations directement de la voie_sg3 (correspondance directe)
        Note: Faudrait voir pour un generateur d'id pour les nouveaux troncons_symu

        :param sym_TRONCON:
        :param cur_id_lane:
        :param nb_lanes:
        :return:
        """
        sym_TRONCON.nb_voie = nb_lanes  # == 1
        # TODO: besoin d'un generateur d'id pour les troncons nouvellement generes
        sym_TRONCON.id += '_lane' + str(cur_id_lane)

        # le nouveau troncon est identique a l'unique voie
        edge_center_axis = self.__dict_lanes[edge_id]['lane_center_axis'][cur_id_lane]
        sym_TRONCON.extremite_amont = edge_center_axis[0]
        sym_TRONCON.extremite_aval = edge_center_axis[-1]
        # transfert des points internes (eventuellement)
        sym_TRONCON.POINTS_INTERNES = self.export_POINTS_INTERNES(edge_center_axis[1:-1])

    @staticmethod
    def init_TRONCON(sg3_edge):
        """

        :param sg3_edge:
        :return:
        """
        sym_TRONCON = reseau.typeTroncon()
        sym_TRONCON.id = sg3_edge['ign_id']
        sym_TRONCON.largeur_voie = sg3_edge['road_width'] / sg3_edge['lane_number']
        sym_TRONCON.id_eltamont = -1
        sym_TRONCON.id_eltaval = -1
        return sym_TRONCON

    @staticmethod
    def export_POINTS_INTERNES(list_points):
        """

        :param :
        :return:
        """
        # print "list_points: ", list_points
        points_internes = reseau.typePointsInternes()
        [points_internes.append(CTD_SYMUVIA_POINT_INTERNE(coordonnees=[x[0], x[1]])) for x in list_points]
        return points_internes