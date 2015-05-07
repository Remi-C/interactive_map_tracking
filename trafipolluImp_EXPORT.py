__author__ = 'latty'

from shapely.geometry import Point, LineString
import pyxb
import parser_symuvia_xsd_2_04_pyxb as symuvia_parser
import trafipolluImp_PYXB as module_pyxb_parser

import os
qgis_plugins_directory = os.path.normcase(os.path.dirname(__file__))
#
infilename_for_symuvia = qgis_plugins_directory + '/' + "project_empty_from_symunet" + "_xsd_" + "2_04" + ".xml"
outfilename_for_symuvia = qgis_plugins_directory + '/' + "export_from_sg3_to_symuvia" + "_xsd_" + "2_04" + ".xml"

pyxb_parser = module_pyxb_parser.trafipolluImp_PYXB(symuvia_parser)


class pyxbDecorator(object):
    """

    """
    def __init__(self, parser_pyxb):
        self.parser_pyxb = parser_pyxb
        self.pyxb_result = ()

    def __call__(self, f):
        """
        """
        def wrapped_f(*args):
            """
            """
            if self.pyxb_result == ():
                str_child_name = f.__name__[7:]     # 7 = len('export_')
                # print 'pyxbDecorator - str_child_name: ', str_child_name
                str_parent = args[-1]
                if type(str_parent) is tuple:
                    str_parent = str_parent[0]
                str_path_to_child = str_parent+'/'+str_child_name
                sym_NODE = self.parser_pyxb.get_instance(str_path_to_child)
                # print 'pyxbDecorator - str_parent: ', str_parent
                # print 'pyxbDecorator - str_path_to_child: ', str_path_to_child
                # print 'sym_NODE: ', sym_NODE
                self.pyxb_result = (str_child_name, sym_NODE)
            # print 'pyxbDecorator - before update, args: ', args
            # update de la liste des arguments
            # on rajoute en fin de liste le tuple : (nom du child, instance de l'element)
            args = list(args)
            args.append(self.pyxb_result)
            # print 'pyxbDecorator - after update, args: ', args
            args = iter(args)
            return f(*args)
        return wrapped_f

    @staticmethod
    def get_path(*args):
        """
        """
        return args[-2]+'/'+args[-1][0]

    @staticmethod
    def get_instance(*args, **kwargs):
        """
        """
        return pyxb_parser.get_instance(pyxbDecorator.get_path(*args), **kwargs)

    @staticmethod
    def get_path_instance(*args):
        """
        """
        # print 'get_path_instance - args: ', args
        str_parent = args[-2]
        str_child = args[-1][0]
        str_path_to_child = str_parent+'/'+str_child
        sym_NODE = pyxb_parser.get_instance(str_path_to_child)
        # print 'str_parent :', str_parent
        # print 'str_child :', str_child
        return str_path_to_child, sym_NODE

    @staticmethod
    def get_path_from_args(*args):
        """
        """
        return args[-1]

class trafipolluImp_EXPORT(object):
    """

    """
    def __init__(self, dict_edges, dict_lanes, dict_nodes, infilename=infilename_for_symuvia):
        """

        """
        self.dict_edges = dict_edges
        self.dict_lanes = dict_lanes
        self.dict_nodes = dict_nodes
        #
        self.pyxb_parser = pyxb_parser
        #
        self.cursor_symuvia = {
            'sg3_node': None,
            'node_id': 0,
            'sym_CAF': None
        }
        #
        self.list_symu_troncons = []
        self.list_symu_connexions = []
        #
        print "trafipolluImp_EXPORT - Open file: ", infilename, "..."
        xml = open(infilename).read()
        self.symu_ROOT = symuvia_parser.CreateFromDocument(xml)
        print "trafipolluImp_EXPORT - Open file: ", infilename, "[DONE]"
        # self.symu_ROOT.RESEAUX.RESEAU[0].TRONCONS.reset()
        # self.symu_ROOT.RESEAUX.RESEAU[0].CONNEXIONS.reset()
        # self.symu_ROOT.TRAFICS.reset()
        #
        self.symu_ROOT_RESEAU_TRONCONS = None
        self.symu_ROOT_RESEAU_CONNEXIONS = None
        self.symu_ROOT_TRAFICS = None

    def select_node(self, node_id):
        """

        :param node_id:
        """
        self.cursor_symuvia['node_id'] = node_id
        self.cursor_symuvia['sg3_node'] = self.dict_nodes[node_id]

    def select_CAF(self, sym_CAF):
        """

        :param sym_CAF:
        :return:
        """
        self.cursor_symuvia['sym_CAF'] = sym_CAF

    def get_CAF(self):
        """

        :return:
        """
        return self.cursor_symuvia['sym_CAF']

    def update_TRONCONS(self):
        """

        :return:
        """
        self.symu_ROOT_RESEAU_TRONCONS = self.export_TRONCONS('RESEAU')

    def update_CONNEXIONS(self):
        """

        :return:
        """
        self.symu_ROOT_RESEAU_CONNEXIONS = self.export_CONNEXIONS('RESEAU')

    def update_TRAFICS(self):
        """

        :return:
        """
        self.symu_ROOT_TRAFICS = self.export_TRAFICS('ROOT_SYMUBRUIT')

    def update_SYMUVIA(self):
        """

        :return:
        """
        print "Update SYMUVIA ..."
        self.update_TRONCONS()
        self.update_CONNEXIONS()
        self.update_TRAFICS()
        #
        print "Update SYMUVIA [DONE]"

    def export(self, update_symu=False, outfilename=outfilename_for_symuvia):
        """

        :param filename:
        :return:
        """

        if update_symu:
            self.update_SYMUVIA()
            #
            b_add_trafics = False
            if self.list_symu_troncons != []:
                self.symu_ROOT.RESEAUX.RESEAU[0].TRONCONS = self.symu_ROOT_RESEAU_TRONCONS
                b_add_trafics = True
            print 'self.list_symu_connexions: ', self.list_symu_connexions
            if self.list_symu_connexions != []:
                self.symu_ROOT.RESEAUX.RESEAU[0].CONNEXIONS = self.symu_ROOT_RESEAU_CONNEXIONS
                b_add_trafics = True
            if b_add_trafics:
                self.symu_ROOT.TRAFICS = self.symu_ROOT_TRAFICS

        #
        self.save_ROOT(self.symu_ROOT, outfilename)

    def save_ROOT(self, sym_ROOT, outfilename):
        """

        :return:
        """
        return self.save_SYMUVIA_Node("ROOT_SYMUBRUIT", sym_ROOT, outfilename)

    @staticmethod
    def save_SYMUVIA_Node(element_name, sym_node, outfilename, prettyxml=True):
        """

        :param sym_node:
        :param outfilename:
        :return:
        """
        print "Write in file: ", outfilename, "..."
        f = open(outfilename, "w")
        str_xml = ""
        if prettyxml:
            try:
                dom = sym_node.toDOM(None, element_name=element_name)
            except pyxb.IncompleteElementContentError as e:
                print '*** ERROR : IncompleteElementContentError'
                print '- Details error: ', e.details()
            except pyxb.MissingAttributeError as e:
                print '*** ERROR : MissingAttributeError'
                print '- Details error: ', e.details()
            else:
                str_xml = dom.toprettyxml(indent="\t", newl="\n", encoding='utf-8')
        else:
            str_xml = sym_node.toxml('utf-8', element_name=element_name)
        #
        f.write(str_xml)
        f.close()
        print "Write in file: ", outfilename, "[DONE]"

    @pyxbDecorator(pyxb_parser)
    def export_TRAFICS(self, *args):
        """

        :param args:
        :return:

        """
        @pyxbDecorator(pyxb_parser)
        def export_TRAFIC(list_troncons, list_connexions, *args):
            #
            @pyxbDecorator(pyxb_parser)
            def export_TRONCONS(list_troncons, *args):
                @pyxbDecorator(pyxb_parser)
                def export_TRONCON(arg_sym_TRONCON, *args):
                    sym_TRONCON = pyxbDecorator.get_instance(*args)
                    # print 'TRAFIC/TRONCONS/TRONCON - sym_TRONCON: ', sym_TRONCON
                    self.update_pyxb_node(
                        sym_TRONCON,
                        id=arg_sym_TRONCON.id,
                        agressivite='true'
                    )
                    return sym_TRONCON
                #
                # print 'TRAFIC/TRONCONS - args: ', args1
                str_path_to_child, sym_TRONCONS = pyxbDecorator.get_path_instance(*args)
                # print 'TRAFIC/TRONCONS - sym_TRONCONS: ', sym_TRONCONS
                # print 'TRAFIC/TRONCONS - str_path_to_child: ', str_path_to_child
                # print 'TRAFIC/TRONCONS - list_troncons: ', list_troncons
                for sym_TRONCON in list_troncons:
                    sym_TRONCONS.append(export_TRONCON(sym_TRONCON, str_path_to_child))
                return sym_TRONCONS
            #
            @pyxbDecorator(pyxb_parser)
            def export_CONNEXIONS_INTERNES(list_connexions, *args):
                @pyxbDecorator(pyxb_parser)
                def export_CONNEXION_INTERNE(arg_sym_CAF, *args):
                    sym_CONNEXION_INTERNE = pyxbDecorator.get_instance(*args)
                    # print 'TRAFIC/TRONCONS/TRONCON - sym_TRONCON: ', sym_TRONCON
                    self.update_pyxb_node(
                        sym_CONNEXION_INTERNE,
                        id=arg_sym_CAF.id
                    )
                    return sym_CONNEXION_INTERNE
                str_path_to_child, sym_CONNEXIONS_INTERNES = pyxbDecorator.get_path_instance(*args)
                for sym_CAF in list_connexions:
                    sym_CONNEXIONS_INTERNES.append(export_CONNEXION_INTERNE(sym_CAF, str_path_to_child))
                return sym_CONNEXIONS_INTERNES
            #
            # print 'TRAFIC - args: ', args
            str_path_to_child, sym_TRAFIC = pyxbDecorator.get_path_instance(*args)
            # print 'TRAFIC - str_path_to_child: ', str_path_to_child
            # print 'TRAFIC - sym_TRAFIC: ', sym_TRAFIC
            self.update_pyxb_node(
                sym_TRAFIC,
                id="trafID",
                accbornee="true",
                coeffrelax="0.55"
            )
            if list_troncons != []:
                sym_TRAFIC.TRONCONS = export_TRONCONS(list_troncons, str_path_to_child)
            if list_connexions != []:
                sym_TRAFIC.CONNEXIONS_INTERNES = export_CONNEXIONS_INTERNES(list_connexions, str_path_to_child)
            return sym_TRAFIC

        str_path_to_child, sym_TRAFICS = pyxbDecorator.get_path_instance(*args)
        # print 'TRAFICS - str_path_to_child: ', str_path_to_child
        # print 'TRAFICS - sym_TRAFICS: ', sym_TRAFICS
        # print 'TRAFICS - self.list_troncons: ', self.list_troncons
        sym_TRAFICS.append(export_TRAFIC(self.list_symu_troncons, self.list_symu_connexions, str_path_to_child))
        return sym_TRAFICS

    @pyxbDecorator(pyxb_parser)
    def export_CONNEXIONS(self, *args):
        """

        :return:

        """
        str_path_to_child, sym_CONNEXIONS = pyxbDecorator.get_path_instance(*args)
        # print 'sym_CONNEXIONS: ', sym_CONNEXIONS
        sym_CONNEXIONS.CARREFOURSAFEUX = self.export_CARREFOURSAFEUX(str_path_to_child)

        return sym_CONNEXIONS

    @pyxbDecorator(pyxb_parser)
    def export_CARREFOURSAFEUX(self, *args):
        """

        :param node_id:
        :return:
        # """
        str_path_to_child, sym_CAFS = pyxbDecorator.get_path_instance(*args)
        for node_id in self.dict_nodes:
            self.select_node(node_id)
            sym_CAF = self.export_CARREFOURAFEUX('CARREFOURSAFEUX')
            sym_CAFS.append(sym_CAF)
            self.list_symu_connexions.append(sym_CAF)
        return sym_CAFS

    @pyxbDecorator(pyxb_parser)
    def export_CARREFOURAFEUX(self, *args):
        """

        :return:
        """
        sym_CAF = None
        #
        nb_edges_connected = len(self.cursor_symuvia['sg3_node']['edge_ids'])
        b_node_is_CAF = nb_edges_connected > 2  # dummy test
        if b_node_is_CAF:
            str_path_to_child, sym_CAF = pyxbDecorator.get_path_instance(*args)
            #
            self.select_CAF(sym_CAF)
            #
            sym_CAF.id = self.build_id_for_CAF(self.cursor_symuvia['node_id'])
            sym_CAF.vit_max = "1"
            #
            sym_CAF.MOUVEMENTS_AUTORISES = self.export_MOUVEMENTS_AUTORISES(str_path_to_child)
            sym_CAF.ENTREES_CAF = self.export_ENTREES_CAF(str_path_to_child)
        #
        # print 'node_id: ', self.current['node_id']
        # print 'sg3_node: ', self.current['sg3_node']
        # print "sg3_node['edge_ids']:", self.current['sg3_node']['edge_ids']
        # print 'nb_edges_connected: ', nb_edges_connected
        #
        return sym_CAF

    @pyxbDecorator(pyxb_parser)
    def export_MOUVEMENTS_AUTORISES(self, *args):
        """

        :param node_id:
        :return:
        """
        str_path_to_child, sym_MOUVEMENTS_AUTORISES = pyxbDecorator.get_path_instance(*args)
        for mouvement_autorise in self.export_MOUVEMENT_AUTORISE(str_path_to_child):
            sym_MOUVEMENTS_AUTORISES.append(mouvement_autorise)
        return sym_MOUVEMENTS_AUTORISES

    @pyxbDecorator(pyxb_parser)
    def export_MOUVEMENT_AUTORISE(self, *args):
        """

        :return:
        """
        str_path_to_child = pyxbDecorator.get_path(*args)
        list_mouvement_autorise = []

        # CAF - IN
        for sym_troncon in self.cursor_symuvia['sg3_node']['CAF']['in']:
            sym_MOUVEMENT_AUTORISE = pyxbDecorator.get_instance(*args)
            sym_MOUVEMENT_AUTORISE.id_troncon_amont = sym_troncon.id
            # [TOPO] - Link between TRONCON & CAF
            sym_troncon.id_eltaval = self.get_CAF().id
            #
            sym_MOUVEMENT_AUTORISE.MOUVEMENT_SORTIES = self.export_MOUVEMENT_SORTIES(str_path_to_child)
            #
            list_mouvement_autorise.append(sym_MOUVEMENT_AUTORISE)
        return list_mouvement_autorise

    @pyxbDecorator(pyxb_parser)
    def export_MOUVEMENT_SORTIES(self, *args):
        """

        :return:

        """
        str_path_to_child, sym_MOUVEMENT_SORTIES = pyxbDecorator.get_path_instance(*args)
        for mvt_sortie in self.export_MOUVEMENT_SORTIE(str_path_to_child):
            sym_MOUVEMENT_SORTIES.append(mvt_sortie)
        return sym_MOUVEMENT_SORTIES

    @pyxbDecorator(pyxb_parser)
    def export_MOUVEMENT_SORTIE(self, *args):
        """

        :return:

        """
        list_mvt_sortie = []
        # CAF - OUT
        for sym_troncon in self.cursor_symuvia['sg3_node']['CAF']['out']:
            sym_MOUVEMENT_SORTIE = pyxbDecorator.get_instance(*args)
            sym_MOUVEMENT_SORTIE.id_troncon_aval = sym_troncon.id
            # [TOPO] - Link between TRONCON & CAF
            sym_troncon.id_eltamont = self.get_CAF().id
            #
            list_mvt_sortie.append(sym_MOUVEMENT_SORTIE)
        return list_mvt_sortie

    @pyxbDecorator(pyxb_parser)
    def export_ENTREES_CAF(self, *args):
        """

        :param node_id:
        :return:

        """
        str_path_to_child, sym_ENTREES_CAF = pyxbDecorator.get_path_instance(*args)
        for entree_caf in self.export_ENTREE_CAF(str_path_to_child):
            sym_ENTREES_CAF.append(entree_caf)
        return sym_ENTREES_CAF

    @pyxbDecorator(pyxb_parser)
    def export_ENTREE_CAF(self, *args):
        """

        :return:

        """
        str_path_to_child = pyxbDecorator.get_path(*args)
        list_entree_caf = []
        # CAF - IN
        for sym_troncon in self.cursor_symuvia['sg3_node']['CAF']['in']:
            sym_ENTREE_CAF = pyxbDecorator.get_instance(*args)
            sym_ENTREE_CAF.id_troncon_amont = sym_troncon.id
            # [TOPO] - Link between TRONCON & CAF
            sym_troncon.id_eltaval = self.get_CAF().id
            #
            sym_ENTREE_CAF.MOUVEMENTS = self.export_MOUVEMENTS(str_path_to_child)
            #
            list_entree_caf.append(sym_ENTREE_CAF)
        return list_entree_caf

    @pyxbDecorator(pyxb_parser)
    def export_MOUVEMENTS(self, *args):
        """

        :return:

        """
        str_path_to_child, sym_MOUVEMENTS = pyxbDecorator.get_path_instance(*args)
        for mouvement in self.export_MOUVEMENT(str_path_to_child):
            sym_MOUVEMENTS.append(mouvement)
        return sym_MOUVEMENTS

    @pyxbDecorator(pyxb_parser)
    def export_MOUVEMENT(self, *args):
        """

        :return:

        """
        list_mouvement = []
        # CAF - OUT
        for sym_troncon in self.cursor_symuvia['sg3_node']['CAF']['out']:
            sym_MOUVEMENT = pyxbDecorator.get_instance(*args)
            sym_MOUVEMENT.id_troncon_aval = sym_troncon.id
            # [TOPO] - Link between TRONCON & CAF
            sym_troncon.id_eltamont = self.get_CAF().id
            #
            list_mouvement.append(sym_MOUVEMENT)
        return list_mouvement

    @pyxbDecorator(pyxb_parser)
    def export_TRONCONS(self, *args):
        """

        :return:

        """
        str_path_to_child, sym_TRONCONS = pyxbDecorator.get_path_instance(*args)
        for edge_id in self.dict_lanes:
            for sym_TRONCON in self.export_TRONCON(edge_id, str_path_to_child):
                sym_TRONCONS.append(sym_TRONCON)
                #
                self.list_symu_troncons.append(sym_TRONCON)
        #
        print 'export_TRONCONS - %d troncons added' % len(self.list_symu_troncons)
        #
        return sym_TRONCONS

    @pyxbDecorator(pyxb_parser)
    def export_TRONCON(self, edge_id, *args):
        """

        :param edge_id:
        :return: [] : list of sym_TRONCON

        """
        str_path_to_child = pyxbDecorator.get_path(*args)

        list_troncons = []

        def update_list_troncon(sym_TRONCON, sg3_edge):
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
                list_sym_TRONCON = filter(lambda x: x.id == sym_TRONCON.id, sg3_edge['sg3_to_symuvia'])
            except:
                # la cle 'sg3_to_symuvia' n'existe pas donc on est dans l'init (premiere passe)
                list_troncons.append(sym_TRONCON)
            else:
                if len(list_sym_TRONCON) == 0:
                    # nouveau troncon
                    list_troncons.append(sym_TRONCON)
                else:
                    # le troncon est deja present
                    # ps: faudrait updater le TRONCON
                    list_troncons.append(list_sym_TRONCON[0])

        sg3_edge = self.dict_edges[edge_id]

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

                    sym_TRONCON = self.build_TRONCON(sg3_edge, *args)

                    if nb_lanes > 1:
                        # groupe de plusieurs voies dans la meme direction
                        self.update_TRONCON_with_lanes_in_groups(sym_TRONCON, edge_id, cur_id_lane, nb_lanes, str_path_to_child)
                    else:
                        # groupe d'une seule voie (pour une direction)
                        self.udpate_TRONCON_with_lane_in_groups(sym_TRONCON, edge_id, cur_id_lane, nb_lanes, str_path_to_child)

                    # Update list_troncon (local function)
                    update_list_troncon(sym_TRONCON, sg3_edge)

                    # next lanes group
                    cur_id_lane += nb_lanes
            else:
                # le troncon possede 1 groupe de voies mono-directionnelles
                nb_lanes = grouped_lanes[0]
                #
                sym_TRONCON = self.build_TRONCON(sg3_edge, *args)
                self.update_TRONCON_with_lanes_in_one_group(sym_TRONCON, sg3_edge, nb_lanes, str_path_to_child)
                # # Link SYMUVIA to SG3 [TOPO]
                # sym_TRONCON['symuvia_to_sg3'] = edge_id

                # Update list_troncon (local function)
                update_list_troncon(sym_TRONCON, sg3_edge)
        finally:
            # LINK STREETGEN3 to SYMUVIA (TOPO)
            sg3_edge['sg3_to_symuvia'] = list_troncons
            #
            return list_troncons

    def update_TRONCON_with_lanes_in_groups(self, sym_TRONCON, edge_id, cur_id_lane, nb_lanes, *args):
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
            linestring = LineString(self.dict_lanes[edge_id]['lane_center_axis'][id_lane])
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
            sym_TRONCON,
            id=sym_TRONCON.id+'_lane'+str(cur_id_lane),
            nb_voie=nb_lanes,
            extremite_amont=troncon_center_axis[0],
            extremite_aval=troncon_center_axis[-1]
        )
        str_path_to_parent = pyxbDecorator.get_path_from_args(*args)
        sym_TRONCON.POINTS_INTERNES = self.export_POINTS_INTERNES(troncon_center_axis[1:-1], str_path_to_parent)

    def update_TRONCON_with_lanes_in_one_group(self, sym_TRONCON, sg3_edge, nb_lanes, *args):
        """
        Plusieurs voies (meme direction) dans 1 unique groupe pour une edge_sg3
        L'idee dans ce cas est d'utiliser les informations geometriques d'edge_sg3 (centre de l'axe de l'edge)
        Faut faire attention au clipping pour ne recuperer qu'a partir d'amont/aval du troncon correspondant
        :return:
        """
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
        troncon_center_axis = filter(
            lambda x: coef_amont <= edge_center_axis.project(Point(x)) <= coef_aval,
            list(edge_center_axis.coords)
        )
        # for point in list(edge_center_axis.coords):
        #     coef_point = edge_center_axis.project(Point(point))
        #     # clipping du point, pour etre sure d'etre amont et aval
        #     if coef_point >= coef_amont and coef_point <= coef_aval:
        #         troncon_center_axis.append(point)
        # print "++ troncon_center_axis: ", troncon_center_axis
        str_path_to_parent = pyxbDecorator.get_path_from_args(*args)
        sym_TRONCON.POINTS_INTERNES = self.export_POINTS_INTERNES(troncon_center_axis, str_path_to_parent)
        #
        cur_id_lane = 0
        self.update_pyxb_node(
            sym_TRONCON,
            id=sym_TRONCON.id+'_lane'+str(cur_id_lane),
            nb_voie=nb_lanes,
            extremite_amont=sg3_edge['amont'],
            extremite_aval=sg3_edge['aval']
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

    def udpate_TRONCON_with_lane_in_groups(self, sym_TRONCON, edge_id, cur_id_lane, nb_lanes, *args):
        """
        1 voie dans une serie de groupe.
        Cas le plus simple, on recupere les informations directement de la voie_sg3 (correspondance directe)
        Note: Faudrait voir pour un generateur d'id pour les nouveaux troncons_symu

        :param sym_TRONCON:
        :param cur_id_lane:
        :param nb_lanes:
        :return:
        """
        edge_center_axis = self.dict_lanes[edge_id]['lane_center_axis'][cur_id_lane]
        try:
            self.update_pyxb_node(
                sym_TRONCON,
                nb_voie=nb_lanes,
                # TODO: besoin d'un generateur d'id pour les troncons nouvellement generes
                id=sym_TRONCON.id+'_lane'+str(cur_id_lane),
                extremite_amont=edge_center_axis[0],
                extremite_aval=edge_center_axis[-1]
            )
            #
            # transfert des points internes (eventuellement)
            str_path_to_parent = pyxbDecorator.get_path_from_args(*args)
            sym_TRONCON.POINTS_INTERNES = self.export_POINTS_INTERNES(edge_center_axis[1:-1], str_path_to_parent)
        except Exception, e:
            print 'udpate_TRONCON_with_lane_in_groups - EXCEPTION: ', e

    @staticmethod
    def build_TRONCON(sg3_edge, *args, **kwargs):
        """

        :param sg3_edge:
        :return:
        """
        sym_TRONCON = pyxbDecorator.get_instance(
            *args,
            id=sg3_edge['ign_id'],
            largeur_voie=sg3_edge['road_width']/sg3_edge['lane_number'],
            id_eltamont="-1",
            id_eltaval="-1",
            **kwargs
        )
        #
        return sym_TRONCON

    @pyxbDecorator(pyxb_parser)
    def export_POINTS_INTERNES(self, list_points, *args):
        """

        :param :
        :return:

        """
        str_path_to_child, sym_POINTS_INTERNES = pyxbDecorator.get_path_instance(*args)

        [sym_POINTS_INTERNES.append(self.export_POINT_INTERNE(x, str_path_to_child)) for x in list_points]
        # alternative approach:
        # [points_internes.append(pyxb.BIND(coordonnees=[x[0], x[1]])) for x in list_points]
        return sym_POINTS_INTERNES

    @pyxbDecorator(pyxb_parser)
    def export_POINT_INTERNE(self, *args):
        """

        :param args:
        :return:
        """
        x = args[0]
        return pyxbDecorator.get_instance(*args, coordonnees=[x[0], x[1]])

    @staticmethod
    def build_id_for_CAF(node_id):
        """

        :param node_id:
        :return:
        """
        return 'CAF_' + str(node_id)
