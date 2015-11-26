__author__ = 'latty'

import numpy as np

from shapely.wkb import loads as sp_wkb_loads

# creation de l'objet logger qui va nous servir a ecrire dans les logs
from imt_tools import init_logger

logger = init_logger(__name__)

from imt_tools import CreateNamedTupleOnGlobals

NT_LANE_SG3 = CreateNamedTupleOnGlobals(
    'NT_LANE_SG3',
    [
        'edge_id',
        'lane_ordinality',
    ]
)


class DumpFromSG3(object):
    """

    """

    def __init__(self, *args, **kwargs):
        """
        """
        self.__dict_nodes = {}
        self.__dict_edges = {}
        self.__dict_lanes = {}
        self.__dict_interconnexions = {}
        self.__dict_roundabouts = {}

    def clear(self):
        """

        :return:
        """
        self.__dict_nodes = {}
        self.__dict_edges = {}
        self.__dict_lanes = {}
        self.__dict_interconnexions = {}
        self.__dict_roundabouts = {}

    @property
    def dict_lanes(self):
        return self.__dict_lanes

    @property
    def dict_edges(self):
        return self.__dict_edges

    @property
    def dict_nodes(self):
        return self.__dict_nodes

    @property
    def dict_interconnexions(self):
        return self.__dict_interconnexions

    def dump_for_nodes(self, objects_from_sql_request):
        """

        :param objects_from_sql_request: resultats d'une requete SQL par rapport aux 'nodes' (connexions SG3)
        :return:
        """
        dict_nodes = self.static_dump_for_nodes(objects_from_sql_request)
        self.__dict_nodes = dict_nodes
        return dict_nodes

    @staticmethod
    def static_dump_for_nodes(objects_from_sql_request):
        """

        :param objects_from_sql_request: resultats d'une requete SQL par rapport aux 'nodes' (connexions SG3)
        :return:

        """
        dict_nodes = {}
        try:
            # get values from SQL request
            for objects_from_sql_request in objects_from_sql_request:
                # edges_ids : liste des edges associes au node courant
                subkeys = ('edges_ids', 'wkb_geom')
                dict_sql_request = dict(filter(lambda i: i[0] in subkeys, objects_from_sql_request.iteritems()))
                dict_sql_request.update(DumpFromSG3.load_geom_buffers_with_shapely(dict_sql_request))
                dict_sql_request.update(
                    DumpFromSG3.load_arrays_with_numpely(
                        dict_sql_request,
                        [
                            ('wkb_geom', 'np_geom')
                        ]
                    )
                )
                dict_nodes[objects_from_sql_request['node_id']] = dict_sql_request
        except Exception, e:
            logger.warning('Exception : %s', e)
        #
        logger.info("nb nodes added: %d" % len(dict_nodes.keys()))
        return dict_nodes

    def dump_for_edges(self, objects_from_sql_request):
        """

        :param objects_from_sql_request: resultats d'une requete SQL par rapport aux 'edges' (troncons SG3)
        :return:
        """
        dict_edges = self.static_dump_for_edges(objects_from_sql_request)
        self.__dict_edges = dict_edges
        return dict_edges

    @staticmethod
    def static_dump_for_edges(objects_from_sql_request):
        """

        :param objects_from_sql_request: resultats d'une requete SQL par rapport aux 'edges' (troncons SG3)
        :return:
        """
        dict_edges = {}
        try:
            # url: http://stackoverflow.com/questions/10252247/how-do-i-get-a-list-of-column-names-from-a-psycopg2-cursor
            # column_names = [desc[0] for desc in cursor.description]
            for object_from_sql_request in objects_from_sql_request:
                # logger.info('object_from_sql_request: %s' % object_from_sql_request)
                subkeys = object_from_sql_request.keys()
                # logger.info('subkeys: %s' % subkeys)
                dict_sql_request = dict(filter(lambda i: i[0] in subkeys, object_from_sql_request.iteritems()))

                dict_sql_request.update(DumpFromSG3.load_geom_buffers_with_shapely(dict_sql_request))
                dict_sql_request.update(
                    DumpFromSG3.load_arrays_with_numpely(
                        dict_sql_request,
                        [
                            ('wkb_amont', 'np_amont'),
                            ('wkb_aval', 'np_aval'),
                            ('wkb_edge_center_axis', 'np_edge_center_axis')
                        ]
                    )
                )
                dict_edges.update({object_from_sql_request['edge_id']: dict_sql_request})
                #
        except Exception, e:
            logger.warning('Exception : %s' % e)

        logger.info("nb edges retrieve from sql request: %d" % len(dict_edges.keys()))
        #
        return dict_edges

    def dump_for_interconnexions(self, objects_from_sql_request):
        """

        :param objects_from_sql_request: resultats d'une requete SQL par rapport aux interconnexions
        :return:
        """
        dict_interconnexions = self.static_dump_for_interconnexions(objects_from_sql_request)
        self.__dict_interconnexions.update(dict_interconnexions)
        return dict_interconnexions

    @staticmethod
    def static_dump_for_interconnexions(objects_from_sql_request):
        """

        :param objects_from_sql_request: resultats d'une requete SQL par rapport aux interconnexions
        :return:

        """
        dict_interconnexions = {}
        dict_set_edges_ids = {}
        nb_total_interconnexion = 0

        try:
            for object_from_sql_request in objects_from_sql_request:
                subkeys = ('edge_id1', 'edge_id2', 'lane_ordinality1', 'lane_ordinality2', 'wkb_interconnexion')
                dict_sql_request = dict(filter(lambda i: i[0] in subkeys, object_from_sql_request.iteritems()))
                #
                dict_sql_request.update(DumpFromSG3.load_geom_buffers_with_shapely(dict_sql_request))
                dict_sql_request.update(
                    DumpFromSG3.load_arrays_with_numpely(
                        dict_sql_request,
                        [
                            ('wkb_interconnexion', 'np_interconnexion')
                        ]
                    )
                )
                #
                node_id = object_from_sql_request['node_id']
                # On met a jour le dictionnaire contenant les interconnexions pour les nodes
                # pour chaque node, on a une liste d'interconnexions (entre edges)
                dict_interconnexions.setdefault(node_id, []).append(dict_sql_request)
                # On met a jour le dictionnaire des edges rattachees au node par une (au moins) interconnexion
                dict_set_edges_ids.setdefault(node_id, set()).add(dict_sql_request['edge_id1'])
                dict_set_edges_ids[node_id].add(dict_sql_request['edge_id2'])
                #
                nb_total_interconnexion += 1
        except Exception, e:
            logger.warning('Exception: %s' % e)
        #
        logger.info("nb CAF added: %d" % len(dict_interconnexions.keys()))
        logger.info("total interconnexions added: %d" % nb_total_interconnexion)

        # on concatene la liste des edges ids dans le dictionnaire resultat: 'dict_interconnexions'
        # permet de n'avoir qu'un objet result de la methode (objet dictionnaire)
        dict_interconnexions.update({'dict_set_edges_ids': dict_set_edges_ids})

        return dict_interconnexions

    def dump_for_lanes(self, objects_from_sql_request, b_static=False):
        """

        :param objects_from_sql_request: resultats d'une requete SQL par rapport aux voies
        :param b_static:
            = True -> met a jour le dictionnaire de la classe
            = False -> renvoie le resultat et ne met pas a jour la classe (comme si c'etait une @staticmethod)
        :return: dictionnaire des voies issues du traitement de la requete (DUMP) SQL

        """
        dict_dump_lanes = {}
        # dict_link_sg3_python = {}
        nb_lanes_informations_retrieve = 0
        try:
            # get sides informations for each 'edge'/'troncon'
            for object_from_sql_request in objects_from_sql_request:
                subkeys = (
                    'edge_id',
                    'lane_side',
                    'lane_position',
                    'lane_direction',
                    'lane_ordinality',
                    'wkb_lane_center_axis')
                dict_sql_request = dict(filter(lambda i: i[0] in subkeys, object_from_sql_request.iteritems()))

                dict_sql_request.update(DumpFromSG3.load_geom_buffers_with_shapely(dict_sql_request))
                dict_sql_request.update(
                    DumpFromSG3.load_arrays_with_numpely(
                        dict_sql_request,
                        [
                            ('wkb_lane_center_axis', 'lane_center_axis')
                        ]
                    )
                )

                edge_id = dict_sql_request['edge_id']

                # on recupere le nombre de voies par rapport a l'edge SG3 (connexion entre les edges et les voies)
                nb_lanes = self.get_lane_number(edge_id)

                lane_ordinality = dict_sql_request['lane_ordinality']

                # lane_ordinality est l'indice SG3 de la lane par rapport a l'edge (edge_id)
                # preallocation d'une liste de taille nb_lanes+1 sur les indices lane_ordinality (1 ... n+1)
                dict_dump_lanes.setdefault(edge_id, [None] * (nb_lanes + 1))

                # on rajoute dans le dictionnaire
                # - key: id de l'edge SG3
                # - value: liste des informations de voies/lanes
                # -- indice: indice de voie suivant son 'ordinality' (SG3)
                dict_dump_lanes[edge_id][lane_ordinality] = dict_sql_request

                # python_id_for_lane = generate_python_id_from_sg3_lane(dict_sql_request, nb_lanes)
                # dict_link_sg3_python[edge_id][lane_ordinality] = python_id_for_lane

                nb_lanes_informations_retrieve += 1
        except Exception, e:
            logger.warning('Exception : %s' % e)

        logger.info('Nb lanes informations retrieve: %d' % nb_lanes_informations_retrieve)

        # maj
        if not b_static:
            self.__dict_lanes.update(dict_dump_lanes)

        return dict_dump_lanes

    # TODO: a refaire par rapport au depot a l'IGN
    @staticmethod
    def static_dump_for_roundabouts(objects_from_sql_request):
        """

        :param objects_from_sql_request:
        :return:
        """
        dict_roundabouts = {}
        try:
            for object_from_sql_request in objects_from_sql_request:
                subkeys = ()
                dict_sql_request = dict(filter(lambda i: i[0] in subkeys, object_from_sql_request.iteritems()))
                dict_sql_request.update(DumpFromSG3.load_geom_buffers_with_shapely(dict_sql_request))
                dict_sql_request.update(
                    DumpFromSG3.load_arrays_with_numpely(
                        dict_sql_request,
                        [
                            ()
                        ]
                    )
                )
        except Exception, e:
            logger.warning('Exception: %s' % e)
        return dict_roundabouts


    @staticmethod
    def load_arrays_with_numpely(dict_sql_request, list_params_to_convert):
        """

        :param dict_objects_from_sql_request:
        :param list_params_to_convert:
        :return:
        """
        dict_arrays_loaded = {}
        for param_name, column_name in list_params_to_convert:
            dict_arrays_loaded[column_name] = np.asarray(dict_sql_request[param_name])
        return dict_arrays_loaded

    @staticmethod
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

    def get_lane_geometry(self, sg3_edge_id, lane_ordinality):
        """

        :param sg3_edge_id:
        :param lane_ordinality:
        :return:

        """
        return self.__dict_lanes[sg3_edge_id][lane_ordinality]['lane_center_axis']

    def get_lane_direction(self, sg3_edge_id, lane_ordinality):
        """

        :param sg3_edge_id:
        :param lane_ordinality:
        :return:

        """
        return self.__dict_lanes[sg3_edge_id][lane_ordinality]['lane_direction']

    def get_lane_number(self, sg3_edges_id):
        """

        :param sg3_edges_id:
        :return:

        """
        return self.__dict_edges[sg3_edges_id]['lane_number']

    def get_interconnexions(self, sg3_node_id):
        """

        :param sg3_node_id:
        :return:

        """
        return self.__dict_interconnexions[sg3_node_id]

    def get_set_edges_ids(self, sg3_node_id):
        """

        :param sg3_node_id:
        :return:

        """
        return self.__dict_interconnexions['dict_set_edges_ids'][sg3_node_id]

    def get_node(self, sg3_node_id):
        """

        :param sg3_node_id:
        :return:
        """
        return self.__dict_nodes[sg3_node_id]

    @staticmethod
    def get_interconnexion_amont(sg3_interconnexion):
        """
        """
        return NT_LANE_SG3(sg3_interconnexion['edge_id1'], sg3_interconnexion['lane_ordinality1'])

    @staticmethod
    def get_interconnexion_aval(sg3_interconnexion):
        """
        """
        return NT_LANE_SG3(sg3_interconnexion['edge_id2'], sg3_interconnexion['lane_ordinality2'])

    @staticmethod
    def get_interconnexion_geometry(sg3_interconnexion):
        """
        """
        return sg3_interconnexion['np_interconnexion']


def get_edge_id(sg3_edge):
    """

    :param sg3_edge:
    :return:
    """
    return sg3_edge['edge_id']


def generate_python_id_from_sg3_lane(sg3_lane, nb_lanes):
    """

    :return:
    """
    # url: https://wiki.python.org/moin/BitManipulation
    lambdas_generate_id = {
        'left': lambda nb_lanes_by_2, position, even: nb_lanes_by_2 - (position / 2),
        'right': lambda nb_lanes_by_2, position, even: nb_lanes_by_2 + (position / 2) - even,
        'center': lambda nb_lanes_by_2, position, even: nb_lanes_by_2
    }

    lane_position = sg3_lane['lane_position']
    lane_side = sg3_lane['lane_side']

    # update list sides for (grouping)
    lambda_generate_id = lambdas_generate_id[lane_side]
    nb_lanes_by_2 = nb_lanes >> 1
    # test si l'entier est pair ?
    # revient a tester le bit de point faible
    even = not (nb_lanes & 1)

    return lambda_generate_id(nb_lanes_by_2, lane_position, even)


    # # need to be in Globals for Pickled 'dict_edges'
    # NT_LANE_INFORMATIONS = imt_tools.CreateNamedTupleOnGlobals(
    # 'NT_LANE_INFORMATIONS',
    #     [
    #         'lane_side',
    #         'lane_direction',
    #         'lane_center_axis',
    #         'nb_lanes'
    #     ]
    # )
    #
    # str_ids_for_lanes = {
    #     'SG3 Informations': "LANES - SG3 Informations",
    #     'SG3 to SYMUVIA': "LANES - SG3 to SYMUVIA",
    #     'SG3 to PYTHON': "LANES - SG3 to PYTHON"
    # }
    #
    # # creation de l'objet logger qui va nous servir a ecrire dans les logs
    # logger = imt_tools.init_logger(__name__)
    #
    #
    # @timerDecorator()
    # def dump_for_roundabouts(objects_from_sql_request):
    #     """
    #
    #     :param objects_from_sql_request:
    #     :return:
    #     """
    #     # for object_from_sql_request in objects_from_sql_request:
    #     #     print 'object_from_sql_request: ', object_from_sql_request
    #     pass
    #
    #
    # def dump_for_edges(objects_from_sql_request):
    #     """
    #
    #     :return:
    #     """
    #     dict_edges = {}
    #     # url: http://stackoverflow.com/questions/10252247/how-do-i-get-a-list-of-column-names-from-a-psycopg2-cursor
    #     # column_names = [desc[0] for desc in cursor.description]
    #     for object_from_sql_request in objects_from_sql_request:
    #         dict_sql_request = dict(object_from_sql_request)
    #
    #         dict_sql_request.update(load_geom_buffers_with_shapely(dict_sql_request))
    #
    #         dict_sql_request.update(
    #             load_arrays_with_numpely(
    #                 dict_sql_request,
    #                 [
    #                     ('wkb_amont', 'np_amont'),
    #                     ('wkb_aval', 'np_aval'),
    #                     ('wkb_edge_center_axis', 'np_edge_center_axis')
    #                 ]
    #             )
    #         )
    #         edge_id = object_from_sql_request['edge_id']
    #         dict_edges.update(
    #             {
    #                 edge_id: dict_sql_request
    #             }
    #         )
    #     #
    #     logger.info("nb edges added: %d" % len(dict_edges.keys()))
    #     #
    #     return dict_edges
    #
    #
    # @timerDecorator()
    # def dump_for_nodes(objects_from_sql_request):
    #     """
    #
    #     :return:
    #     """
    #     dict_nodes = {}
    #     # get values from SQL request
    #     for object_from_sql_request in objects_from_sql_request:
    #         #
    #         node_id = object_from_sql_request['node_id']
    #         dict_sql_request = {
    #             'edges_ids': object_from_sql_request['edges_ids'],
    #             'wkb_geom': object_from_sql_request['wkb_geom']
    #         }
    #         dict_sql_request.update(load_geom_buffers_with_shapely(dict_sql_request))
    #         #
    #         dict_sql_request.update(
    #             load_arrays_with_numpely(
    #                 dict_sql_request,
    #                 [
    #                     ('wkb_geom', 'np_geom')
    #                 ]
    #             )
    #         )
    #         #
    #         # print '%s - dict_sql_request: %s' % (node_id, dict_sql_request['np_geom'])
    #         #
    #         dict_nodes[node_id] = dict_sql_request
    #     #
    #     logger.info("nb nodes added: %d" % len(dict_nodes.keys()))
    #
    #     # for k, v in dict_nodes.iteritems():
    #     #     print 'dict_nodes[%s].np_geom: %s' % (k, v['np_geom'])
    #     #
    #     return dict_nodes
    #
    #
    # @timerDecorator()
    # def dump_for_interconnexions(objects_from_sql_request):
    #     """
    #
    #     :param objects_from_sql_request:
    #     :return:
    #
    #     """
    #     dict_interconnexions = {}
    #     dict_set_edges_ids = {}
    #     nb_total_interconnexion = 0
    #
    #     for object_from_sql_request in objects_from_sql_request:
    #         #
    #         node_id = object_from_sql_request['node_id']
    #         #
    #         dict_sql_request = {
    #             'edge_id1': object_from_sql_request['edge_id1'],
    #             'edge_id2': object_from_sql_request['edge_id2'],
    #             'lane_ordinality1': object_from_sql_request['lane_ordinality1'],
    #             'lane_ordinality2': object_from_sql_request['lane_ordinality2'],
    #             'wkb_interconnexion': object_from_sql_request['wkb_interconnexion']
    #         }
    #         #
    #         dict_sql_request.update(load_geom_buffers_with_shapely(dict_sql_request))
    #         #
    #         dict_sql_request.update(
    #             load_arrays_with_numpely(
    #                 dict_sql_request,
    #                 [
    #                     ('wkb_interconnexion', 'np_interconnexion')
    #                 ]
    #             )
    #         )
    #         #
    #         dict_interconnexions.setdefault(node_id, []).append(dict_sql_request)
    #         #
    #         dict_set_edges_ids.setdefault(node_id, set()).add(dict_sql_request['edge_id1'])
    #         dict_set_edges_ids[node_id].add(dict_sql_request['edge_id2'])
    #         #
    #         nb_total_interconnexion += 1
    #
    #     #
    #     logger.info("nb interconnexions added: %d" % len(dict_interconnexions.keys()))
    #     logger.info("total interconnexions added: %d" % nb_total_interconnexion)
    #     #
    #     return dict_interconnexions, dict_set_edges_ids
    #
    #
    # def load_arrays_with_numpely(dict_sql_request, list_params_to_convert):
    #     """
    #
    #     :param dict_objects_from_sql_request:
    #     :param list_params_to_convert:
    #     :return:
    #     """
    #     dict_arrays_loaded = {}
    #     for param_name, column_name in list_params_to_convert:
    #         dict_arrays_loaded[column_name] = np.asarray(dict_sql_request[param_name])
    #     return dict_arrays_loaded
    #
    #
    # def load_geom_buffers_with_shapely(dict_objects_from_sql_request):
    #     """
    #
    #     :param dict_objects_from_sql_request:
    #     :return:
    #     """
    #     dict_buffers_loaded = {}
    #     # urls:
    #     # - http://toblerity.org/shapely/manual.html
    #     # - http://gis.stackexchange.com/questions/89323/postgis-parse-geometry-wkb-with-ogr
    #     # - https://docs.python.org/2/c-api/buffer.html
    #     for column_name, object_from_sql_request in dict_objects_from_sql_request.iteritems():
    #         if isinstance(object_from_sql_request, buffer):
    #             dict_buffers_loaded[column_name] = sp_wkb_loads(bytes(object_from_sql_request))
    #     return dict_buffers_loaded
    #
    #
    # def generate_id_for_lane(object_sql_lane, nb_lanes):
    #     """
    #
    #     :return:
    #     """
    #     lane_position = object_sql_lane['lane_position']
    #     lane_side = object_sql_lane['lane_side']
    #     # url: https://wiki.python.org/moin/BitManipulation
    #     lambdas_generate_id = {
    #         'left': lambda nb_lanes_by_2, position, even: nb_lanes_by_2 - (position >> 1),
    #         'right': lambda nb_lanes_by_2, position, even: nb_lanes_by_2 + (position >> 1) - even,
    #         'center': lambda nb_lanes_by_2, position, even: nb_lanes_by_2
    #     }
    #     # update list sides for (grouping)
    #     lambda_generate_id = lambdas_generate_id[lane_side]
    #     nb_lanes_by_2 = nb_lanes >> 1
    #     # test si l'entier est pair ?
    #     # revient a tester le bit de point faible
    #     even = not (nb_lanes & 1)
    #
    #     return lambda_generate_id(nb_lanes_by_2, lane_position, even)
    #
    #
    # @timerDecorator()
    # def dump_lanes(objects_from_sql_request):
    #     """
    #
    #     :param objects_from_sql_request:
    #     :param dict_edges:
    #     :return:
    #
    #     """
    #     dict_dump_lanes = {}
    #     # get sides informations for each 'edge'/'troncon'
    #     for object_from_sql_request in objects_from_sql_request:
    #         validkeys = ('lane_side', 'lane_position', 'lane_direction', 'lane_ordinality', 'wkb_lane_center_axis')
    #         dict_sql_request = dict(filter(lambda i: i[0] in validkeys, object_from_sql_request.iteritems()))
    #
    #         dict_sql_request.update(load_geom_buffers_with_shapely(dict_sql_request))
    #         dict_sql_request.update(
    #             load_arrays_with_numpely(
    #                 dict_sql_request,
    #                 [
    #                     ('wkb_lane_center_axis', 'lane_center_axis'),
    #                 ]
    #             )
    #         )
    #
    #     return dict_dump_lanes
    #
    #
    # def topo_for_lanes(dict_dump_lanes, dict_edges):
    #     """
    #
    #     :param dict_lanes:
    #     :return:
    #
    #     """
    #     dict_lanes = {}
    #
    #     for edge_id, object_from_sql_request in dict_dump_lanes.iteritems():
    #         # edge_id = lane['edge_id']
    #
    # nb_lanes = dict_edges[edge_id]['lane_number']
    #         #
    #         dict_lanes.setdefault(
    #             edge_id,
    #             {
    #                 str_ids_for_lanes['SG3 Informations']: [None] * nb_lanes,
    #                 # pre-allocate size for list,
    #                 str_ids_for_lanes['SG3 to SYMUVIA']: [None] * nb_lanes,  # pre-allocate size for list,
    #                 str_ids_for_lanes['SG3 to PYTHON']: [None] * (nb_lanes + 1)
    #             }
    #         )
    #
    #         dict_lanes.update(
    #             {
    #                 object_from_sql_request['edge_id']: object_from_sql_request
    #             }
    #         )
    #
    #         python_lane_id = generate_id_for_lane(object_from_sql_request, nb_lanes)
    #
    #         set_python_lane_id(dict_lanes, edge_id, object_from_sql_request['lane_ordinality'], python_lane_id)
    #
    #         # Attention ici !
    #         # on places les lanes dans des listes pythons (avec ordre python) et non dans l'ordre fournit par la requete
    #         # SQL (ce qui etait avant) et/ou l'ordre fournit par SG3 (ordonality id)
    #         set_lane_informations(
    #             dict_lanes, edge_id, python_lane_id,
    #             NT_LANE_INFORMATIONS(
    #                 object_from_sql_request['lane_side'],
    #                 object_from_sql_request['lane_direction'],
    #                 object_from_sql_request['lane_center_axis'],
    #                 nb_lanes
    #             )
    #         )
    #
    #         # for future: http://stackoverflow.com/questions/8023306/get-key-by-value-in-dictionary
    #         # find a key with value
    #
    #     # create the dict: dict_grouped_lanes
    #     # contain : for each edge_id list of lanes in same direction
    #     dict_grouped_lanes = build_dict_grouped_lanes(dict_lanes)
    #
    #     return dict_lanes, dict_grouped_lanes
    #
    #
    # def build_dict_grouped_lanes(dict_lanes, str_id_for_grouped_lanes='grouped_lanes'):
    #     """
    #
    #     :param dict_lanes:
    #     :return:
    #     Retourne un dictionnaire dont les
    #     - key: indice d'une edge SG3
    #     - value: liste de groupes de lanes dans le meme sens.
    #         Chaque element de la liste decrit le nombre de voies consecutives dans le meme sens.
    #     """
    #     dict_grouped_lanes = {}
    #     map(lambda x, y: dict_grouped_lanes.__setitem__(x, {str_id_for_grouped_lanes: y}),
    #         dict_lanes,
    #         [
    #             [
    #                 sum(1 for i in value_groupby)
    #                 for key_groupby, value_groupby in
    #                 groupby(get_list_lanes_informations_from_edge_id(dict_lanes, sg3_edge_id), lambda x: x.lane_direction)
    #             ]
    #             for sg3_edge_id in dict_lanes
    #         ])
    #     return dict_grouped_lanes
    #
    #
    # def set_lane_informations(dict_lanes, sg3_edge_id, python_lane_id, informations):
    #     """
    #
    #     :param dict_lanes:
    #     :param sg3_edge_id:
    #     :param python_lane_id:
    #     :return:
    #     """
    #     get_list_lanes_informations_from_edge_id(dict_lanes, sg3_edge_id)[python_lane_id] = informations
    #
    #
    # def get_list_lanes_informations_from_lane(lane):
    #     """
    #
    #     :param lane:
    #     :return:
    #
    #     """
    #     return lane[str_ids_for_lanes['SG3 Informations']]
    #
    #
    # def get_list_lanes_informations_from_edge_id(dict_lanes, sg3_edge_id):
    #     """
    #
    #     :param dict_lanes:
    #     :param sg3_edge_id:
    #     :return:
    #     """
    #     return dict_lanes[sg3_edge_id][str_ids_for_lanes['SG3 Informations']]
    #
    #
    # def get_lane_from_python_lane_id(dict_lanes, sg3_edge_id, python_lane_id):
    #     """
    #
    #     :param dict_lanes:
    #     :param sg3_edge_id:
    #     :param python_lane_id:
    #     :return:
    #     """
    #     return dict_lanes[sg3_edge_id][str_ids_for_lanes['SG3 Informations']][python_lane_id]
    #
    #
    # def get_lane_direction_from_python_lane_id(dict_lanes, sg3_edge_id, python_lane_id):
    #     """
    #
    #     :param dict_lanes:
    #     :param sg3_edge_id:
    #     :param python_lane_id:
    #     :return:
    #
    #     """
    #     return get_lane_from_python_lane_id(dict_lanes, sg3_edge_id, python_lane_id).lane_direction
    #
    #
    # def get_lane_geometry_from_python_lane_id(dict_lanes, sg3_edge_id, python_lane_id):
    #     """
    #
    #     :param dict_lanes:
    #     :param sg3_edge_id:
    #     :param python_lane_id:
    #     :return:
    #
    #     """
    #     return get_lane_from_python_lane_id(dict_lanes, sg3_edge_id, python_lane_id).lane_center_axis
    #
    #
    # def get_Symuvia_list_lanes_from_edge_id(dict_lanes, sg3_edge_id):
    #     """
    #
    #     :param dict_lanes:
    #     :param sg3_edge_id:
    #     :return:
    #
    #     """
    #     return dict_lanes[sg3_edge_id][str_ids_for_lanes['SG3 to SYMUVIA']]
    #
    #
    # def get_symu_troncon_from_python_id(dict_lanes, sg3_edge_id, python_lane_id):
    #     """
    #
    #     :param dict_lanes:
    #     :param sg3_edge_id:
    #     :return:
    #
    #     """
    #     return dict_lanes[sg3_edge_id][str_ids_for_lanes['SG3 to SYMUVIA']][python_lane_id]
    #
    #
    # def get_PYTHON_list_lanes(dict_lanes, sg3_edge_id):
    #     """
    #
    #     :param dict_lanes:
    #     :param sg3_edge_id:
    #     :return:
    #     """
    #     return dict_lanes[sg3_edge_id][str_ids_for_lanes['SG3 to PYTHON']]
    #
    #
    # def get_python_id_from_lane_ordinality(dict_lanes, sg3_edge_id, lane_ordinality):
    #     """
    #
    #     :param dict_lanes:
    #     :param sg3_edge_id:
    #     :return:
    #     """
    #     return get_PYTHON_list_lanes(dict_lanes, sg3_edge_id)[lane_ordinality]
    #
    #
    # def set_python_lane_id(dict_lanes, sg3_edge_id, lane_ordinality, python_lane_id):
    #     """
    #
    #     :param dict_lanes:
    #     :param sg3_edge_id:
    #     :return:
    #     """
    #     get_PYTHON_list_lanes(dict_lanes, sg3_edge_id)[lane_ordinality] = python_lane_id