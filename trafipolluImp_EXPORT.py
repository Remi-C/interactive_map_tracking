__author__ = 'latty'

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
    def get_path_instance(*args, **kwargs):
        """
        """
        # print 'get_path_instance - args: ', args
        str_parent = args[-2]
        str_child = args[-1][0]
        str_path_to_child = str_parent+'/'+str_child
        sym_NODE = pyxb_parser.get_instance(str_path_to_child, **kwargs)
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
    def __init__(self, dict_edges, dict_lanes, dict_nodes, module_topo, infilename=infilename_for_symuvia):
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
        # self.list_symu_troncons = []
        self.list_symu_connexions = []
        #
        print "trafipolluImp_EXPORT - Open file: ", infilename, "..."
        xml = open(infilename).read()
        self.symu_ROOT = symuvia_parser.CreateFromDocument(xml)
        print "trafipolluImp_EXPORT - Open file: ", infilename, "[DONE]"
        #
        self.symu_ROOT_RESEAU_TRONCONS = None
        self.symu_ROOT_RESEAU_CONNEXIONS = None
        self.symu_ROOT_TRAFICS = None

        self.module_topo = module_topo  # tpi_TOPO.trafipolluImp_TOPO(self.dict_edges, self.dict_lanes, self.dict_nodes)

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
            if self.module_topo.list_pyxb_symutroncons:
                self.symu_ROOT.RESEAUX.RESEAU[0].TRONCONS = self.symu_ROOT_RESEAU_TRONCONS
                b_add_trafics = True
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
        return self.save_SYMUVIA_Node('ROOT_SYMUBRUIT', sym_ROOT, outfilename)

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
                def export_CONNEXION_INTERNE(sym_CAF, *args):
                    sym_CONNEXION_INTERNE = pyxbDecorator.get_instance(*args)
                    # print 'TRAFIC/TRONCONS/TRONCON - sym_TRONCON: ', sym_TRONCON
                    self.update_pyxb_node(
                        sym_CONNEXION_INTERNE,
                        id=sym_CAF.id
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
                # print 'list_connexions: ', list_connexions
                sym_TRAFIC.CONNEXIONS_INTERNES = export_CONNEXIONS_INTERNES(list_connexions, str_path_to_child)
            return sym_TRAFIC

        str_path_to_child, sym_TRAFICS = pyxbDecorator.get_path_instance(*args)
        # print 'TRAFICS - str_path_to_child: ', str_path_to_child
        # print 'TRAFICS - sym_TRAFICS: ', sym_TRAFICS
        # print 'TRAFICS - self.list_troncons: ', self.list_troncons
        # sym_TRAFICS.append(export_TRAFIC(self.list_symu_troncons, self.list_symu_connexions, str_path_to_child))
        sym_TRAFICS.append(
            # export_TRAFIC(self.module_topo.list_pyxb_symutroncons, self.list_symu_connexions, str_path_to_child)
            export_TRAFIC(self.module_topo.list_pyxb_symutroncons.values(), self.list_symu_connexions, str_path_to_child)
        )
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

        # TODO: construction TOPO ici !
        self.module_topo.build_topo_for_nodes()

        str_path_to_child, sym_CAFS = pyxbDecorator.get_path_instance(*args)
        for node_id in self.dict_nodes:
            self.select_node(node_id)
            sym_CAF = self.export_CARREFOURAFEUX(str_path_to_child)
            if sym_CAF:
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
        sg3_node = self.cursor_symuvia['sg3_node']
        nb_edges_connected = len(sg3_node['array_str_edge_ids'])
        b_node_is_CAF = nb_edges_connected > 2  # dummy test
        if b_node_is_CAF:
            id_CAF = self.build_id_for_CAF(self.cursor_symuvia['node_id'])
            str_path_to_child, sym_CAF = pyxbDecorator.get_path_instance(
                *args,
                id=id_CAF,
                vit_max="1"
            )
            #
            self.select_CAF(sym_CAF)
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
        sg3_node_caf_in = self.cursor_symuvia['sg3_node']['CAF']['in']
        for sym_troncon in sg3_node_caf_in:
            ids_lanes = range(sym_troncon.nb_voie+1)[1:]
            for id_lane in ids_lanes:
                sym_MOUVEMENT_AUTORISE = pyxbDecorator.get_instance(
                    *args,
                    id_troncon_amont=sym_troncon.id,
                    num_voie_amont=id_lane
                )
                #
                sym_MOUVEMENT_AUTORISE.MOUVEMENT_SORTIES = self.export_MOUVEMENT_SORTIES(str_path_to_child)
                #
                list_mouvement_autorise.append(sym_MOUVEMENT_AUTORISE)
                # [TOPO] - Link between TRONCON & CAF
                sym_troncon.id_eltaval = self.get_CAF().id
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
            ids_lanes = range(sym_troncon.nb_voie+1)[1:]
            for id_lane in ids_lanes:
                sym_MOUVEMENT_SORTIE = pyxbDecorator.get_instance(*args)
                sym_MOUVEMENT_SORTIE.id_troncon_aval = sym_troncon.id
                sym_MOUVEMENT_SORTIE.num_voie_aval = id_lane
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
            ids_lanes = range(sym_troncon.nb_voie+1)[1:]
            for id_lane in ids_lanes:
                sym_ENTREE_CAF = pyxbDecorator.get_instance(*args)
                #
                sym_ENTREE_CAF.id_troncon_amont = sym_troncon.id
                sym_ENTREE_CAF.num_voie_amont = id_lane
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
            ids_lanes = range(sym_troncon.nb_voie+1)[1:]
            for id_lane in ids_lanes:
                sym_MOUVEMENT = pyxbDecorator.get_instance(*args)
                #
                sym_MOUVEMENT.id_troncon_aval = sym_troncon.id
                sym_MOUVEMENT.num_voie_aval = id_lane
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
        # TODO: construction TOPO ici !
        self.module_topo.convert_sg3_edges_to_pyxb_symutroncons()

        sym_TRONCONS = pyxbDecorator.get_instance(*args)
        # for pyxb_symuTRONCON in self.module_topo.list_pyxb_symutroncons:
        for pyxb_symuTRONCON in self.module_topo.list_pyxb_symutroncons.values():
            sym_TRONCONS.append(pyxb_symuTRONCON)
        #
        return sym_TRONCONS

    @staticmethod
    def update_pyxb_node(node, **kwargs):
        """

        :param kwargs:
        :return:
        """
        # print 'update_pyxb_node - kwargs: ', kwargs
        for k, v in kwargs.iteritems():
            node._setAttribute(k, v)

    @staticmethod
    def build_id_for_CAF(node_id):
        """

        :param node_id:
        :return:
        """
        return 'CAF_' + str(node_id)
