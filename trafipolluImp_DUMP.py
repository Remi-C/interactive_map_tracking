__author__ = 'latty'

import numpy as np
from collections import namedtuple
from itertools import groupby

from shapely.wkb import loads


NAMEDTUPLE_LANESIDE_OUTCOMING = namedtuple(
    'NAMEDTUPLE_LANESIDE_OUTCOMING',
    [
        'lane_side',
        'oncoming'
    ]
)

lambdas_generate_id = {
    'left': lambda nb_lanes_by_2, position, even: nb_lanes_by_2 - int(position / 2),
    'right': lambda nb_lanes_by_2, position, even: nb_lanes_by_2 + int(position / 2) - even,
    'center': lambda nb_lanes_by_2, position, even: nb_lanes_by_2
}


def dump_for_edges(objects_from_sql_request, dict_edges):
    """

    :return:
    """
    # url: http://stackoverflow.com/questions/10252247/how-do-i-get-a-list-of-column-names-from-a-psycopg2-cursor
    # column_names = [desc[0] for desc in cursor.description]
    # namedtuple = imt_tools.create_named_tuple_from_names('DUMP_SQL_TRAFIPOLLU', column_names)
    for object_from_sql_request in objects_from_sql_request:
        # url: http://www.dotnetperls.com/namedtuple
        # tuple_trafipollu = namedtuple._make(tuple_from_sql_request)
        # self._dict_edges.update({tuple_trafipollu.edge_id: tuple_trafipollu})

        edge_id = object_from_sql_request['edge_id']

        dict_sql_request = object_from_sql_request.copy()

        dict_edges.update({edge_id: dict_sql_request})

        #
        load_geom_with_shapely_from_dict(dict_edges[edge_id])

        dict_sql_request['amont'] = np.asarray(dict_edges[edge_id]['point_amont'])
        dict_sql_request['aval'] = np.asarray(dict_edges[edge_id]['point_aval'])
        dict_sql_request['amont_to_aval'] = dict_sql_request['aval'] - dict_sql_request['amont']
        dict_sql_request['linez_geom'] = np.asarray(dict_edges[edge_id]['linez_geom'])

        # print 'self._dict_edges: ', self._dict_edges
        #


def load_geom_with_shapely_from_dict(dict_objects_from_sql_request):
    """

    :param dict_objects_from_sql_request:
    :return:
    """
    # ul: http://toblerity.org/shapely/manual.htmlhttp://toblerity.org/shapely/manual.html
    # url: http://gis.stackexchange.com/questions/89323/postgis-parse-geometry-wkb-with-ogr
    # url: https://docs.python.org/2/c-api/buffer.html
    for name_key in dict_objects_from_sql_request.keys():
        object = dict_objects_from_sql_request[name_key]
        if isinstance(object, buffer):
            dict_objects_from_sql_request[name_key] = loads(bytes(object))


def dump_lanes(objects_from_sql_request, dict_edges, dict_lanes):
    # get sides informations for each 'edge'/'troncon'
    for object_from_sql_request in objects_from_sql_request:
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
        oncoming = False
        lane_center_axis = np.asarray(loads(bytes(lane_center_axis)))
        dict_lanes[id_edge].setdefault('lane_center_axis', []).append(lane_center_axis)
        oncoming = edges_is_same_orientation(
            dict_edges[id_edge]['amont_to_aval'],
            compute_direction_linestring(lane_center_axis)
        )
        # update list sides for (grouping)
        position = object_from_sql_request['lane_position']
        lambda_generate_id = lambdas_generate_id[lane_side]
        nb_lanes_by_2 = (nb_lanes / 2)
        even = not bool(nb_lanes % 2)
        id_in_list = lambda_generate_id(nb_lanes_by_2, position, even)
        dict_lanes[id_edge]['id_list'][id_in_list] = NAMEDTUPLE_LANESIDE_OUTCOMING(lane_side, oncoming)
        # print 'position: ', position
        # print 'id: ', id
    # print "** _dict_sides:", self.__dict_sides

    # create the dict: __dict_grouped_lanes
    # contain : for each edge_id list of lanes in same direction
    dict_grouped_lanes = {}
    map(lambda x, y: dict_grouped_lanes.__setitem__(x, {'grouped_lanes': y}),
        dict_lanes,
        [
            [sum(1 for i in g) for k, g in
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
    for k, v in dict_grouped_lanes.items():
        dict_edges[k].update(v)
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