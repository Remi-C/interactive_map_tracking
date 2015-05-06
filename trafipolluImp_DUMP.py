__author__ = 'latty'

import numpy as np
from itertools import groupby

from shapely.wkb import loads as sp_wkb_loads

import imt_tools





# need to be in Globals for Pickled 'dict_edges'
NT_LANESIDE_OUTCOMING = imt_tools.CreateNamedOnGlobals(
    'NAMEDTUPLE_LANESIDE_OUTCOMING',
    [
        'lane_side',
        'oncoming'
    ]
)


def dump_for_edges(objects_from_sql_request, dict_edges):
    """

    :return:
    """
    # url: http://stackoverflow.com/questions/10252247/how-do-i-get-a-list-of-column-names-from-a-psycopg2-cursor
    # column_names = [desc[0] for desc in cursor.description]
    # namedtuple = imt_tools.create_named_tuple_from_names('DUMP_SQL_TRAFIPOLLU', column_names)
    dict_sql_request = {}
    for object_from_sql_request in objects_from_sql_request:
        # url: http://www.dotnetperls.com/namedtuple
        # tuple_trafipollu = namedtuple._make(tuple_from_sql_request)
        # self._dict_edges.update({tuple_trafipollu.edge_id: tuple_trafipollu})
        edge_id = object_from_sql_request['edge_id']

        dict_sql_request = object_from_sql_request.copy()

        dict_edges.update({edge_id: dict_sql_request})

        load_geom_with_shapely_from_dict(dict_edges[edge_id])

        dict_sql_request['amont'] = np.asarray(dict_sql_request['point_amont'])
        dict_sql_request['aval'] = np.asarray(dict_sql_request['point_aval'])
        dict_sql_request['amont_to_aval'] = dict_sql_request['aval'] - dict_sql_request['amont']
        dict_sql_request['linez_geom'] = np.asarray(dict_sql_request['linez_geom'])
    # print 'self._dict_edges: ', self._dict_edges
    #

def dump_for_nodes(objects_from_sql_request, dict_nodes):
    """

    :return:
    """
    for object_from_sql_request in objects_from_sql_request:
        node_id = object_from_sql_request['node_id']
        edge_ids = object_from_sql_request['edge_ids']
        dict_nodes.setdefault(node_id, {'edge_ids': edge_ids})
    #
    # print 'self.dict_nodes: ', dict_nodes

def build_topo_for_nodes(dict_nodes, dict_edges, dict_lanes):
    """

    :param dict_nodes:
    :param dict_edges:
    :return:
    """
    str_key_for_lane = '_lane'
    l_str_key_for_lane = len(str_key_for_lane)

    for node_id, dict_values in dict_nodes.iteritems():
        caf_entrees = []
        caf_sorties = []
        caf_entrees_sorties = [caf_entrees, caf_sorties]
        for edge_id in dict_values['edge_ids']:
            sge_edge = dict_edges[edge_id]
            list_symuvia_edges = [pyxb_troncon for pyxb_troncon in sge_edge['sg3_to_symuvia']]
            for symuvia_troncon in list_symuvia_edges:
                symuvia_troncon_id = symuvia_troncon.id
                try:
                    id_in_list = int(symuvia_troncon_id[symuvia_troncon_id.find(str_key_for_lane)+l_str_key_for_lane:])
                except:
                    # print "PROBLEME! symuvia_troncon_id: %s - probleme de conversion en 'int'" % symuvia_troncon_id
                    id_in_list = 0
                finally:
                    oncoming = dict_lanes[edge_id]['id_list'][id_in_list].oncoming
                    # '!=' est l'operateur XOR en Python
                    id_caf_inout = int((sge_edge['start_node'] == node_id) != oncoming)
                    caf_entrees_sorties[id_caf_inout].append(symuvia_troncon)
                # print 'id_caf_inout: ', id_caf_inout
                # print "sge_edge['start_node']: ", sge_edge['start_node']
                # print 'id_in_list: ', id_in_list
                # print 'oncoming: ', oncoming
            # print "id edge in SG3: ", edge_id
            # print "-> id edges in SYMUVIA: ", list_symuvia_edges
        #
        dict_nodes[node_id].setdefault('CAF', {'in': caf_entrees, 'out': caf_sorties})
        #
        # print "node_id: ", node_id
        # print "-> caf_entrees (SYMUVIA): ", caf_entrees
        # print "-> caf_sorties (SYMUVIA): ", caf_sorties
        # print "-> dict_nodes[node_id]: ", dict_nodes[node_id]

def load_geom_with_shapely_from_dict(dict_objects_from_sql_request):
    """

    :param dict_objects_from_sql_request:
    :return:
    """
    # urls:
    # - http://toblerity.org/shapely/manual.html
    # - http://gis.stackexchange.com/questions/89323/postgis-parse-geometry-wkb-with-ogr
    # - https://docs.python.org/2/c-api/buffer.html
    for column_name, object_from_sql_request in dict_objects_from_sql_request.iteritems():
        if isinstance(object_from_sql_request, buffer):
            dict_objects_from_sql_request[column_name] = sp_wkb_loads(bytes(object_from_sql_request))


def dump_lanes(objects_from_sql_request, dict_edges, dict_lanes):
    # url: https://wiki.python.org/moin/BitManipulation
    lambdas_generate_id = {
        'left': lambda nb_lanes_by_2, position, even: nb_lanes_by_2 - (position >> 1),
        'right': lambda nb_lanes_by_2, position, even: nb_lanes_by_2 + (position >> 1) - even,
        'center': lambda nb_lanes_by_2, position, even: nb_lanes_by_2
    }

    # get sides informations for each 'edge'/'troncon'
    for object_from_sql_request in objects_from_sql_request:
        #
        id_edge = object_from_sql_request['edge_id']
        lane_side = object_from_sql_request['lane_side']
        #
        nb_lanes = dict_edges[id_edge]['lane_number']
        dict_lanes.setdefault(id_edge,
                              {
                                  'id_list': [None] * nb_lanes  # pre-allocate size for list
                              })
        #
        lane_center_axis = object_from_sql_request['lane_center_axis']
        lane_center_axis = np.asarray(sp_wkb_loads(bytes(lane_center_axis)))
        dict_lanes[id_edge].setdefault('lane_center_axis', []).append(lane_center_axis)
        oncoming = edges_is_same_orientation(
            dict_edges[id_edge]['amont_to_aval'],
            compute_direction_linestring(lane_center_axis)
        )
        # update list sides for (grouping)
        position = object_from_sql_request['lane_position']
        lambda_generate_id = lambdas_generate_id[lane_side]
        nb_lanes_by_2 = nb_lanes >> 1
        # test si l'entier est pair ?
        # revient a tester le bit de point faible
        even = not(nb_lanes & 1)
        id_in_list = lambda_generate_id(nb_lanes_by_2, position, even)
        dict_lanes[id_edge]['id_list'][id_in_list] = NT_LANESIDE_OUTCOMING(lane_side, oncoming)
        #
        # print 'position: ', position
        # print 'id: ', id
    # print "** _dict_sides:", self.__dict_sides

    # create the dict: dict_grouped_lanes
    # contain : for each edge_id list of lanes in same direction
    dict_grouped_lanes = {}
    map(lambda x, y: dict_grouped_lanes.__setitem__(x, {'grouped_lanes': y}),
        dict_lanes,
        [
            [sum(1 for i in g) for id_edge, g in
             groupby(dict_lanes[id_edge]['id_list'], lambda x: x.oncoming)]
            for id_edge in dict_lanes
        ])
    # print "** self._dict_grouped_lanes:", dict_grouped_lanes

    # update dict_edges with lanes grouped informations
    # map(lambda x, y: dict_edges.__setitem__(y,
    # dict(dict_edges[y],
    # **dict_grouped_lanes[y])),
    #     dict_edges,
    #     dict_grouped_lanes
    # )
    for id_edge, grouped_lanes in dict_grouped_lanes.items():
        dict_edges[id_edge].update(grouped_lanes)
        # print "** self._dict_edges: ", dict_edges

def edges_is_same_orientation(edge0, edge1):
    """

    :param edge0:
    :param edge1:
    :return:
    """
    return edge0.dot(edge1) > 0

def compute_direction_linestring(np_linestring):
    """

    :param linestring:
    :return:
    """
    amont = np_linestring[0]
    aval = np_linestring[-1]
    return amont - aval