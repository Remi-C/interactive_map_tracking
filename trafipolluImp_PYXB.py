__author__ = 'atty'

class trafipolluImp_PYXB(object):
    """

    """
    def __init__(self, parser):
        """

        :param parser:
        :return:
        """
        self.pyxb_tree_ctd = {}
        #
        ctd_root_node = parser.ROOT_SYMUBRUIT.typeDefinition()
        self.dump_pyxb_tree(('ROOT_SYMUBRUIT', ctd_root_node))
        # for k, v in self.pyxb_tree_ctd.iteritems():
        #     print "path: %s -> CTD: %s" % (k, v)

    def dump_pyxb_tree(self, tuple_Name_CTD, prefix=""):
        """

        :param root:
        :param prefix:
        :return:
        """
        #
        prefix_node = prefix + tuple_Name_CTD[0]
        self.pyxb_tree_ctd[prefix_node] = tuple_Name_CTD[1]
        #
        for child_pyxb in tuple_Name_CTD[1]._ElementMap:
            uri_child = child_pyxb.uriTuple()[1]
            node_child = tuple_Name_CTD[1]._ElementBindingDeclForName(uri_child)[0]()
            self.dump_pyxb_tree((uri_child, node_child), prefix_node + '/')

    def get_CTD(self, path_to_CTD, update_dict=True):
        """

        :param path_to_CTD:
        :return:
        """
        try:
            return self.pyxb_tree_ctd[path_to_CTD]
        except KeyError:
            print "Not found the element with this path: ", path_to_CTD
            print "Searching CTD in dict ..."
            # cherche les clees avec le suffixe path_to_CTD
            # potentiellement il peut avoir plusieurs cles repondant au critere de suffixe
            l_key = filter(
                lambda x: x.endswith(path_to_CTD),
                self.pyxb_tree_ctd.keys()
            )
            l_ctd = map(lambda x: self.pyxb_tree_ctd[x], l_key)
            # si on ne trouve qu'une clee
            # -> on met a jour le dictionnaire pour retrouver directement le resultat a la prochaine requete
            if update_dict and len(l_key) == 1:
                self.pyxb_tree_ctd[path_to_CTD] = l_ctd[0]
            # debug: tuple listes des classes et cles (paths)
            return l_ctd, l_key
