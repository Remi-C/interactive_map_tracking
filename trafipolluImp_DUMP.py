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


def dump_for_edges(objects_from_sql_request):
    """

    :return:
    """
    dict_edges = {}
    # url: http://stackoverflow.com/questions/10252247/how-do-i-get-a-list-of-column-names-from-a-psycopg2-cursor
    # column_names = [desc[0] for desc in cursor.description]
    for object_from_sql_request in objects_from_sql_request:
        # dict_sql_request = object_from_sql_request.copy()
        dict_sql_request = dict(object_from_sql_request)

        dict_sql_request.update(load_geom_buffers_with_shapely(dict_sql_request))

        dict_sql_request.update(
            load_arrays_with_numpely(
                dict_sql_request,
                [
                    ('amont', 'point_amont'),
                    ('aval', 'point_aval'),
                    ('linez_geom', 'linez_geom')
                ]
            )
        )

        dict_sql_request['amont_to_aval'] = dict_sql_request['aval'] - dict_sql_request['amont']

        edge_id = object_from_sql_request['edge_id']
        dict_edges.update({edge_id: dict_sql_request})
    #
    print '# dump_for_edge - nb edges added: ', len(dict_edges.keys())
    #
    return dict_edges


def dump_for_nodes(objects_from_sql_request):
    """

    :return:
    """
    dict_nodes = {}
    for object_from_sql_request in objects_from_sql_request:
        node_id = object_from_sql_request['node_id']
        edge_ids = object_from_sql_request['edge_ids']
        dict_nodes[node_id] = {'edge_ids': edge_ids}
    #
    print '# dump_for_nodes - nb nodes added: ', len(dict_nodes.keys())
    #
    return dict_nodes


def build_topo_for_nodes(dict_nodes, dict_edges, dict_lanes):
    """

    :param dict_nodes:
    :param dict_edges:
    :return:
    """

    # !!!!! FAUDRAIT CLEAN LE RESEAU des troncons sans voies, ou node/caf avec de tel troncons !!!!

    str_key_for_lane = '_lane_'
    l_str_key_for_lane = len(str_key_for_lane)

    def get_id_lane_from_id_name(symu_troncon):
        """
        """
        id_in_list = 0
        symu_troncon_id = symu_troncon.id
        try:
            id_in_list = int(symu_troncon_id[symu_troncon_id.find(str_key_for_lane)+l_str_key_for_lane:])
        except:
            print "# build_topo_for_nodes - PROBLEME! symuvia_troncon_id: %s - probleme de conversion en 'int'" % symu_troncon_id
        finally:
            return id_in_list

    list_remove_nodes = []
    for node_id, dict_values in dict_nodes.iteritems():
        caf_entrees = []
        caf_sorties = []
        caf_entrees_sorties = [caf_entrees, caf_sorties]
        #
        for edge_id in dict_values['edge_ids']:
            sg3_edge = dict_edges[edge_id]
            try:
                # list_symu_edges = [edges for edges in sge_edge['sg3_to_symuvia']]
                list_symu_edges = sg3_edge['sg3_to_symuvia']
            except Exception, e:
                print '# build_topo_for_nodes - EXCEPTION: ', e
                # remove this node
                list_remove_nodes.append(node_id)
            else:
                for symu_troncon in list_symu_edges:
                    id_in_list = get_id_lane_from_id_name(symu_troncon)
                    oncoming = dict_lanes[edge_id]['id_list'][id_in_list].oncoming
                    # '!=' est l'operateur XOR en Python
                    id_caf_in_out = int((sg3_edge['start_node'] == node_id) != oncoming)
                    caf_entrees_sorties[id_caf_in_out].append(symu_troncon)
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
    # remove nodes
    nodes_removed = [dict_nodes.pop(k, None) for k in list_remove_nodes]
    print '# build_topo_for_nodes - nb nodes_removed: ', len(nodes_removed)
    print '# build_topo_for_nodes - nb nodes : ', len(dict_nodes.keys())


def load_arrays_with_numpely(dict_sql_request, list_params_to_convert):
    """

    :param dict_objects_from_sql_request:
    :param list_params_to_convert:
    :return:
    """
    dict_arrays_loaded = {}
    for column_name, param_name in list_params_to_convert:
        dict_arrays_loaded[column_name] = np.asarray(dict_sql_request[param_name])
    return dict_arrays_loaded


def load_geom_buffers_with_shapely(dict_objects_from_sql_request):
    """

    :param dict_objects_from_sql_request:
    :return:
    """
    dict_buffers_loaded = {}
    # urls:
    # - http://toblerity.org/shapely/manual.html
    # - http://gis.stackexchange.com/questions/89323/postgis-parse-geometry-wkb-with-ogr
    # - https://docs.python.org/2/c-api/buffer.html
    for column_name, object_from_sql_request in dict_objects_from_sql_request.iteritems():
        if isinstance(object_from_sql_request, buffer):
            dict_buffers_loaded[column_name] = sp_wkb_loads(bytes(object_from_sql_request))
    return dict_buffers_loaded


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
        edge_id = object_from_sql_request['edge_id']
        lane_side = object_from_sql_request['lane_side']
        #
        nb_lanes = dict_edges[edge_id]['lane_number']
        dict_lanes.setdefault(edge_id,
                              {
                                  'id_list': [None] * nb_lanes  # pre-allocate size for list
                              })
        #
        lane_center_axis = object_from_sql_request['lane_center_axis']
        lane_center_axis = np.asarray(sp_wkb_loads(bytes(lane_center_axis)))
        dict_lanes[edge_id].setdefault('lane_center_axis', []).append(lane_center_axis)
        oncoming = edges_is_same_orientation(
            dict_edges[edge_id]['amont_to_aval'],
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
        dict_lanes[edge_id]['id_list'][id_in_list] = NT_LANESIDE_OUTCOMING(lane_side, oncoming)
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
            [sum(1 for i in g) for edge_id, g in
             groupby(dict_lanes[edge_id]['id_list'], lambda x: x.oncoming)]
            for edge_id in dict_lanes
        ])
    # print "** self._dict_grouped_lanes:", dict_grouped_lanes

    # update dict_edges with lanes grouped informations
    # map(lambda x, y: dict_edges.__setitem__(y,
    # dict(dict_edges[y],
    # **dict_grouped_lanes[y])),
    #     dict_edges,
    #     dict_grouped_lanes
    # )
    for edge_id, grouped_lanes in dict_grouped_lanes.items():
        dict_edges[edge_id].update(grouped_lanes)
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