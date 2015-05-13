__author__ = 'latty'

import parser_symuvia_xsd_2_04_pyxb as symuvia_parser
from shapely.geometry import Point, LineString
import pyxb

class trafipolluImp_TOPO(object):
    """

    """
    def __init__(self, dict_edges, dict_lanes, dict_nodes):
        """

        """
        self.dict_edges = dict_edges
        self.dict_lanes = dict_lanes
        self.dict_nodes = dict_nodes
        #
        # self.list_pyxb_symutroncons = []
        self.dict_pyxb_symutroncons = {}
        self.dict_pyxb_symuconnexions = []
        #

    def clear(self):
        """

        :return:
        """
        self.dict_pyxb_symutroncons = []
        self.dict_pyxb_symuconnexions = []

    def convert_sg3_edges_to_pyxb_symutroncons(self):
        """

        :return:

        """
        for sg3_edge_id in self.dict_lanes:
            # self.list_pyxb_symutroncons.extend(self.convert_sg3_edge_to_pyxb_symutroncon(sg3_edge_id))
            self.dict_pyxb_symutroncons.update(self.convert_sg3_edge_to_pyxb_symutroncon(sg3_edge_id))
        #
        print 'convert_sg3_edges_to_pyxb_symutroncons - %d troncons added' % len(self.dict_pyxb_symutroncons.keys())
        #

    def convert_sg3_edge_to_pyxb_symutroncon(self, sg3_edge_id):
        """

        :param sg3_edge_id:
        :return:
        """
        dict_pyxb_simuTroncons = {}

        def update_list_troncon(pyxb_simuTroncon, sg3_edge):
            """
            Update de liste_troncon:
                liste_troncon est le resultat de la fonction donc elle insere ou non des troncons dans le systeme
                L'update regarde si le troncon n'a pas deja ete calculee (prealablement)
                si oui: on met a jour les donnees sans rajouter un nouvel object (nouvelle adresse memoire)
                si non: on rajoute l'object (sym_TRONCON) dans la liste (instance de l'object)
                L'update permet de garder une coherence avec les liens topologiques calcules pour les nodes/CAF
                ps: a revoir, une forte impression que c'est tres foireux (meme si impression de deja vu dans les
                codes transmis par LICIT)
            """
            try:
                list_pyxb_simuTRONCON = filter(lambda x: x.id == pyxb_simuTroncon.id, sg3_edge['sg3_to_symuvia'])
            except:
                # la cle 'sg3_to_symuvia' n'existe pas donc on est dans l'init (premiere passe)
                dict_pyxb_simuTroncons[pyxb_simuTroncon.id] = pyxb_simuTroncon
            else:
                if len(list_pyxb_simuTRONCON) == 0:
                    # nouveau troncon
                    dict_pyxb_simuTroncons[pyxb_simuTroncon.id] = pyxb_simuTroncon
                else:
                    # le troncon est deja present
                    # TODO: il faudrait updater le TRONCON
                    dict_pyxb_simuTroncons[list_pyxb_simuTRONCON[0].id] = list_pyxb_simuTRONCON[0]

        sg3_edge = self.dict_edges[sg3_edge_id]

        # print "sg3_edge: ", sg3_edge
        try:
            grouped_lanes = sg3_edge['grouped_lanes']
        except:
            # Il y a des edge_sg3 sans voie(s) dans le reseau SG3 ... faudrait demander a Remi !
            # Peut etre des edges_sg3 aidant uniquement aux connexions/creation (de zones) d'intersections
            print ""
            print "!!! 'BUG' with edge id: ", sg3_edge_id, " - no 'group_lanes' found !!!"
            print ""
        else:
            if len(grouped_lanes) > 1:
                # on a plusieurs groupes de voies (dans des directions differentes) pour ce troncon
                cur_id_lane = 0
                for id_group_lane in grouped_lanes:
                    nb_lanes = id_group_lane

                    # sym_TRONCON = self.build_TRONCON(sg3_edge, *args)
                    pyxb_symuTRONCON = symuvia_parser.typeTroncon(
                        id=sg3_edge['str_ign_id'],
                        largeur_voie=sg3_edge['f_road_width']/sg3_edge['ui_lane_number'],
                        id_eltamont="-1",
                        id_eltaval="-1"
                    )

                    if nb_lanes > 1:
                        # groupe de plusieurs voies dans la meme direction
                        self.update_TRONCON_with_lanes_in_groups(pyxb_symuTRONCON, sg3_edge_id, cur_id_lane, nb_lanes)
                    else:
                        # groupe d'une seule voie (pour une direction)
                        self.udpate_TRONCON_with_lane_in_groups(pyxb_symuTRONCON, sg3_edge_id, cur_id_lane, nb_lanes)

                    # Update list_troncon (local function)
                    update_list_troncon(pyxb_symuTRONCON, sg3_edge)

                    # next lanes group
                    cur_id_lane += nb_lanes
            else:
                # le troncon possede 1 groupe de voies mono-directionnelles
                nb_lanes = grouped_lanes[0]
                #
                # sym_TRONCON = self.build_TRONCON(sg3_edge, *args)
                pyxb_symuTRONCON = symuvia_parser.typeTroncon(
                    id=sg3_edge['str_ign_id'],
                    largeur_voie=sg3_edge['f_road_width']/sg3_edge['ui_lane_number'],
                    id_eltamont="-1",
                    id_eltaval="-1"
                )
                self.update_TRONCON_with_lanes_in_one_group(pyxb_symuTRONCON, sg3_edge, nb_lanes)
                # Update list_troncon (local function)
                update_list_troncon(pyxb_symuTRONCON, sg3_edge)
        finally:
            # LINK STREETGEN3 to SYMUVIA (TOPO)
            sg3_edge['sg3_to_symuvia'] = dict_pyxb_simuTroncons.values()
            #
            return dict_pyxb_simuTroncons

    def update_TRONCON_with_lanes_in_groups(self, pyxb_symuTRONCON, sg3_edge_id, cur_id_lane, nb_lanes):
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
            linestring = LineString(self.dict_lanes[sg3_edge_id]['lane_center_axis'][id_lane])
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
        cur_id_lane = 0
        self.update_pyxb_node(
            pyxb_symuTRONCON,
            id=self.build_id_for_TRONCON(pyxb_symuTRONCON, cur_id_lane),
            nb_voie=nb_lanes,
            extremite_amont=troncon_center_axis[0],
            extremite_aval=troncon_center_axis[-1]
        )

        pyxb_symuTRONCON.POINTS_INTERNES = self.build_pyxb_POINTS_INTERNES(troncon_center_axis[1:-1])

    def update_TRONCON_with_lanes_in_one_group(self, pyxb_symuTRONCON, sg3_edge, nb_lanes):
        """
        Plusieurs voies (meme direction) dans 1 unique groupe pour une edge_sg3
        L'idee dans ce cas est d'utiliser les informations geometriques d'edge_sg3 (centre de l'axe de l'edge)
        Faut faire attention au clipping pour ne recuperer qu'a partir d'amont/aval du troncon correspondant
        :return:
        """
        #
        edge_center_axis = LineString(sg3_edge['np_edge_center_axis'])
        # note : on pourrait recuperer le sens avec les attributs 'left' 'right' des lanes_sg3
        # ca eviterait le sort (sur 2 valeurs c'est pas ouf mais bon)
        list_amont_aval_proj = sorted(
            [
                edge_center_axis.project(Point(sg3_edge['np_amont'])),
                edge_center_axis.project(Point(sg3_edge['np_aval']))
            ]
        )
        # print "++ list_amont_aval_proj: ", list_amont_aval_proj
        # on recupere les coefficients 1D des amont/aval
        coef_amont, coef_aval = list_amont_aval_proj
        troncon_center_axis = []
        # liste des points formant l'axe de l'edge_sg3
        troncon_center_axis = filter(
            lambda x: coef_amont <= edge_center_axis.project(Point(x)) <= coef_aval,
            list(edge_center_axis.coords)
        )

        pyxb_symuTRONCON.POINTS_INTERNES = self.build_pyxb_POINTS_INTERNES(troncon_center_axis)

        cur_id_lane = 0
        self.update_pyxb_node(
            pyxb_symuTRONCON,
            id=self.build_id_for_TRONCON(pyxb_symuTRONCON, cur_id_lane),
            nb_voie=nb_lanes,
            extremite_amont=sg3_edge['np_amont'],
            extremite_aval=sg3_edge['np_aval']
        )

    @staticmethod
    def update_pyxb_node(node, **kwargs):
        """

        :param kwargs:
        :return:
        """
        # print 'update_pyxb_node - kwargs: ', kwargs
        for k, v in kwargs.iteritems():
            node._setAttribute(k, v)

    def udpate_TRONCON_with_lane_in_groups(self, pyxb_symuTRONCON, edge_id, cur_id_lane, nb_lanes):
        """
        1 voie dans une serie de groupe.
        Cas le plus simple, on recupere les informations directement de la voie_sg3 (correspondance directe)
        Note: Faudrait voir pour un generateur d'id pour les nouveaux troncons_symu

        :param pyxb_symuTRONCON:
        :param cur_id_lane:
        :param nb_lanes:
        :return:
        """
        edge_center_axis = self.dict_lanes[edge_id]['lane_center_axis'][cur_id_lane]
        try:
            self.update_pyxb_node(
                pyxb_symuTRONCON,
                nb_voie=nb_lanes,
                id=self.build_id_for_TRONCON(pyxb_symuTRONCON, cur_id_lane),
                extremite_amont=edge_center_axis[0],
                extremite_aval=edge_center_axis[-1]
            )

            # transfert des points internes (eventuellement)
            pyxb_symuTRONCON.POINTS_INTERNES = self.build_pyxb_POINTS_INTERNES(edge_center_axis[1:-1])
        except Exception, e:
            print 'udpate_TRONCON_with_lane_in_groups - EXCEPTION: ', e

    @staticmethod
    def build_id_for_TRONCON(pyxb_symuTRONCON, lane_id):
        """

        :param node_id:
        :return:
        """
        return pyxb_symuTRONCON.id + '_lane_' + str(lane_id)

    def build_pyxb_POINTS_INTERNES(self, list_points, *args):
        """

        :param :
        :return:

        """
        pyxb_symuPOINTS_INTERNES = symuvia_parser.typePointsInternes()

        [pyxb_symuPOINTS_INTERNES.append(pyxb.BIND(coordonnees=[x[0], x[1]])) for x in list_points]
        return pyxb_symuPOINTS_INTERNES

    def build_topo_for_nodes(self):
        """

        :param dict_nodes:
        :param dict_edges:
        :param dict_lanes:
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
        for node_id, dict_values in self.dict_nodes.iteritems():
            caf_entrees = []
            caf_sorties = []
            caf_entrees_sorties = [caf_entrees, caf_sorties]
            #
            for edge_id in dict_values['array_str_edge_ids']:
                sg3_edge = self.dict_edges[edge_id]
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
                        oncoming = self.dict_lanes[edge_id]['id_list'][id_in_list].oncoming
                        # '!=' est l'operateur XOR en Python
                        id_caf_in_out = int((sg3_edge['ui_start_node'] == node_id) != oncoming)
                        caf_entrees_sorties[id_caf_in_out].append(symu_troncon)
                        # print 'id_caf_inout: ', id_caf_inout
                        # print "sge_edge['start_node']: ", sge_edge['start_node']
                        # print 'id_in_list: ', id_in_list
                        # print 'oncoming: ', oncoming
                    # print "id edge in SG3: ", edge_id
                    # print "-> id edges in SYMUVIA: ", list_symuvia_edges
                    #
                    self.dict_nodes[node_id].setdefault('CAF', {'in': caf_entrees, 'out': caf_sorties})
                    #
                    # print "node_id: ", node_id
                    # print "-> caf_entrees (SYMUVIA): ", caf_entrees
                    # print "-> caf_sorties (SYMUVIA): ", caf_sorties
                    # print "-> dict_nodes[node_id]: ", dict_nodes[node_id]
        # remove nodes
        nodes_removed = [self.dict_nodes.pop(k, None) for k in list_remove_nodes]
        #
        print '# build_topo_for_nodes - nb nodes_removed: ', len(nodes_removed)
        print '# build_topo_for_nodes - nb nodes : ', len(self.dict_nodes.keys())
