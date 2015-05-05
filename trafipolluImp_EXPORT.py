__author__ = 'latty'

from shapely.geometry import Point, LineString
import pyxb
import parser_symuvia_xsd_2_04_pyxb as network
import trafipolluImp_PYXB as pyxb_parser

###################################################
### ALIAS des classes de binding
### verifier les liens si problemes d'export!
###################################################
# def format_string(str):
#     """
#     retire les espaces :
#     - plus de 2 reduit a 1
#     - en debut et fin de string
#     les tabulations, les retours a la ligne
#     :param str:
#     :return:
#     """
#     str = unicode(str).encode('ascii', 'replace')
#     import re
#     str = re.sub(' +', ' ', str)
#     str = re.sub('\n', '', str)
#     str = re.sub('\t', '', str)
#     str = str.rstrip().lstrip()
#     return str
#
#
# def get_class_from_parser(str_doc_class):
#     """
#
#     :param str_doc_class:
#     :return:
#     """
#     return_class = None
#     try:
#         return_class = network.__dict__[
#             filter(lambda x: format_string(network.__dict__[x].__doc__) == str_doc_class, dir(network))[0]]
#     except:
#         print "ERROR! Can't find the class with doc class string:", str_doc_class, " from Parser (SYMUVIA) !!!"
#         return_class = None
#     else:
#         print "Found the class with doc class string:", str_doc_class, " from Parser (SYMUVIA) !!!"
#         print "-> ", return_class
#     finally:
#         return return_class
#
# CTD_SYMUVIA_TRONCONS = get_class_from_parser(u'Liste des tron?ons')
# CTD_SYMUVIA_POINT_INTERNE_TRONCON = get_class_from_parser(u"Description d'un point interne du tron?on")

### NEW TECHNIQUES !
PYXB_SYMUVIA_ROOT_SYMUBRUIT = network.ROOT_SYMUBRUIT
PYXB_SYMUVIA_RESEAUX = PYXB_SYMUVIA_ROOT_SYMUBRUIT.memberElement('RESEAUX')
PYXB_SYMUVIA_RESEAU = PYXB_SYMUVIA_RESEAUX.memberElement('RESEAU')
PYXB_RESEAU_TRONCONS = PYXB_SYMUVIA_RESEAU.memberElement('TRONCONS')
# on recupere a partir du type: typePointsInternes
# c'est un raccourci (au lieu de faire comme au dessus avec l'arborescence)
PYXB_POINT_INTERNE = network.typePointsInternes._ElementBindingDeclForName('POINT_INTERNE')[0]

CTD_RESEAU_TRONCONS = PYXB_RESEAU_TRONCONS.typeDefinition()
CTD_POINT_INTERNE = PYXB_POINT_INTERNE.typeDefinition()

###################################################

import os
qgis_plugins_directory = os.path.normcase(os.path.dirname(__file__))
#
infilename_for_symuvia = qgis_plugins_directory + '/' + "project_empty_from_symunet" + "_xsd_" + "2_04" + ".xml"
outfilename_for_symuvia = qgis_plugins_directory + '/' + "export_from_sg3_to_symuvia" + "_xsd_" + "2_04" + ".xml"


class trafipolluImp_EXPORT(object):
    """

    """
    def __init__(self, dict_edges, dict_lanes):
        """

        """
        self.dict_edges = dict_edges
        self.dict_lanes = dict_lanes
        #
        self.pyxb_parser = pyxb_parser.trafipolluImp_PYXB(network)
        #
        element_symuvia = 'TRONCON/POINTS_INTERNES/POINT_INTERNE'
        print '%s, CTD:%s' % (element_symuvia, self.pyxb_parser.get_CTD(element_symuvia))
        print '%s, CTD:%s' % (element_symuvia, self.pyxb_parser.get_CTD(element_symuvia))

    def export(self, infilename=infilename_for_symuvia, outfilename=outfilename_for_symuvia):
        """

        :param filename:
        :return:
        """
        print "Open file: ", infilename, "..."
        xml = open(infilename).read()
        sym_ROOT = network.CreateFromDocument(xml)
        print "Open file: ", infilename, "[DONE]"

        print "Export SG3 to SYMUVIA ..."
        sym_ROOT.RESEAUX.RESEAU[0].TRONCONS.reset()
        sym_ROOT.RESEAUX.RESEAU[0].TRONCONS = self.export_TRONCONS()
        print "Export SG3 to SYMUVIA [DONE]"

        self.save_ROOT(sym_ROOT, outfilename)

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
            else:
                str_xml = dom.toprettyxml(indent="\t", newl="\n", encoding='utf-8')
        else:
            str_xml = sym_node.toxml('utf-8', element_name=element_name)
        #
        f.write(str_xml)
        f.close()
        print "Write in file: ", outfilename, "[DONE]"

    def export_TRONCONS(self):
        """

        :return:

        """
        sym_TRONCONS = CTD_RESEAU_TRONCONS()
        for edge_id in self.dict_lanes:
            for sym_TRONCON in self.export_TRONCON(edge_id):
                sym_TRONCONS.append(sym_TRONCON)
        return sym_TRONCONS

    def export_TRONCON(self, edge_id):
        """

        :param edge_id:
        :return: [] : list of sym_TRONCON

        """
        list_troncons = []

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
            # LINK STREETGEN3 to SYMUVIA (TOPO)
            sg3_edge['sg3_to_symuvia'] = list_troncons
            #
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
        sym_TRONCON.nb_voie = nb_lanes
        sym_TRONCON.POINTS_INTERNES = self.build_POINTS_INTERNES(troncon_center_axis[1:-1])
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

        sym_TRONCON.POINTS_INTERNES = self.build_POINTS_INTERNES(troncon_center_axis)
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
        edge_center_axis = self.dict_lanes[edge_id]['lane_center_axis'][cur_id_lane]
        sym_TRONCON.extremite_amont = edge_center_axis[0]
        sym_TRONCON.extremite_aval = edge_center_axis[-1]
        # transfert des points internes (eventuellement)
        sym_TRONCON.POINTS_INTERNES = self.build_POINTS_INTERNES(edge_center_axis[1:-1])

    @staticmethod
    def init_TRONCON(sg3_edge):
        """

        :param sg3_edge:
        :return:
        """
        sym_TRONCON = network.typeTroncon()
        #
        sym_TRONCON.id = sg3_edge['ign_id']
        sym_TRONCON.largeur_voie = sg3_edge['road_width'] / sg3_edge['lane_number']
        sym_TRONCON.id_eltamont = "-1"
        sym_TRONCON.id_eltaval = "-1"
        #
        return sym_TRONCON

    @staticmethod
    def build_POINTS_INTERNES(list_points):
        """

        :param :
        :return:
        """
        # print "list_points: ", list_points
        points_internes = network.typePointsInternes()
        [points_internes.append(CTD_POINT_INTERNE(coordonnees=[x[0], x[1]])) for x in list_points]
        # alternative approach:
        # [points_internes.append(pyxb.BIND(coordonnees=[x[0], x[1]])) for x in list_points]
        return points_internes