__author__ = 'atty'

import os
import cPickle as pickle

from signalsmanager import SignalsManager
import imt_tools
from trafipolluImp_SQL import trafipolluImp_SQL
import trafipolluImp_EXPORT as tpi_EXPORT
import trafipolluImp_TOPO as tpi_TOPO


class TrafiPolluImp(object):
    """

    """

    def __init__(self, iface, dlg):
        """

        """
        self.dlg = dlg
        self.signals_manager = SignalsManager.instance()
        #
        self.__dict_edges = {}  # key: id_edge  -   value: (topo) informations from SG3
        self.__dict_lanes = {}
        self.__dict_nodes = {}
        #
        self.module_SQL = trafipolluImp_SQL(iface, self.__dict_edges, self.__dict_lanes, self.__dict_nodes)
        self.module_topo = tpi_TOPO.trafipolluImp_TOPO(self.__dict_edges, self.__dict_lanes, self.__dict_nodes)
        self.module_export = tpi_EXPORT.trafipolluImp_EXPORT(
            self.__dict_edges,
            self.__dict_lanes,
            self.__dict_nodes,
            self.module_topo)

    def _init_signals_(self):
        """

        """
        self.signals_manager.add_clicked(self.dlg.execute_sql_commands, self.slot_execute_SQL_commands, "GUI")
        self.signals_manager.add_clicked(self.dlg.refreshSqlScriptList, self.slot_refreshSqlScriptList, "GUI")
        self.signals_manager.add_clicked(self.dlg.pickle_trafipollu, self.slot_Pickled_TrafiPollu, "GUI")
        self.signals_manager.add_clicked(self.dlg.export_to_symuvia, self.slot_export_to_symuvia, "GUI")
        self.signals_manager.add_clicked(self.dlg.tf_dump_topo_export, self.slot_dump_topo_export, "GUI")
        self.signals_manager.add_clicked(self.dlg.tf_clear, self.slot_clear, "GUI")
        #
        self.signals_manager.add(self.dlg.combobox_sql_scripts,
                                  "currentIndexChanged (int)",
                                  self.slot_currentIndexChanged_SQL,
                                  "GUI")

    def _clear_(self):
        """

        :return:
        """
        print 'clean ressources ...'
        #
        self.__dict_edges.clear()
        self.__dict_lanes.clear()
        self.__dict_nodes.clear()
        #
        self.module_topo.clear()

    def slot_clear(self):
        """

        :return:
        """
        self._clear_()

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
        self._execute_SQL_commands(
            self.dlg.plainTextEdit_sql_script.toPlainText(),
            imt_tools.get_itemText(self.dlg.combobox_sql_scripts)
        )

    def _execute_SQL_commands(self, sqlFile, sql_choice_combobox):
        """

        :return:
        """
        self.module_SQL.execute_SQL_commands(sqlFile, sql_choice_combobox)

    def slot_refreshSqlScriptList(self):
        """

        """

        self.dlg.combobox_sql_scripts.clear()

        import os

        path = os.path.normcase(os.path.dirname(__file__))
        files = os.listdir(path)

        [
            self.dlg.combobox_sql_scripts.addItem(os.path.basename(i)[:-4], path + '/' + i)
            for i in files if i.endswith('.sql')
        ]

    def get_sql_filename(self, sql_name):
        """

        :param sql_name:
        :return:
        """
        path = os.path.normcase(os.path.dirname(__file__))
        return path + '/' + sql_name + '.sql'

    def get_sql_file(self, sql_filename):
        """

        :return:
        """
        sqlFile = ""
        fd = None
        try:
            fd = open(sql_filename)
            if fd:
                sqlFile = fd.read()
                fd.close()
        except:
            sqlFile = "Error ! Can't read the SQL file"
        #
        return sqlFile

    def slot_currentIndexChanged_SQL(self, id_index):
        """

        :param id_index:
        """
        sql_filename = imt_tools.get_itemData(self.dlg.combobox_sql_scripts)
        self.dlg.plainTextEdit_sql_script.setPlainText(self.get_sql_file(sql_filename))

    def slot_export_to_symuvia(self):
        """

        :return:
        """
        self.module_export.export(True)

    def _dump_topo_export_(self):
        """

        :return:
        """
        #
        list_sql_commands = [
            'update_table_edges_from_qgis',
            'dump_informations_from_edges',
            'dump_sides_from_edges',
            'dump_informations_from_nodes',
        ]
        #
        for sql_command in list_sql_commands:
            sql_filename = self.get_sql_filename(sql_command)
            sql_file = self.get_sql_file(sql_filename)
            print 'sql_filename: ', sql_filename
            print 'sql_file: ', sql_file
            self._execute_SQL_commands(
                sql_file,
                sql_command
            )
        #
        self.module_export.export(True)

    def slot_dump_topo_export(self):
        """

        :return:
        """
        self._dump_topo_export_()

    def slot_Pickled_TrafiPollu(self):
        """

        """
        # test Pickle
        qgis_plugins_directory = os.path.normcase(os.path.dirname(__file__))
        infilename_for_pickle = qgis_plugins_directory + '/' + "dump_pickle.p"
        print "Pickle TrafiPollu in: ", infilename_for_pickle, "..."
        pickle.dump(self, open(infilename_for_pickle, "wb"))
        print "Pickle TrafiPollu in: ", infilename_for_pickle, "[DONE]"

    def __getstate__(self):
        """

        :return:
        """
        # note: normalement les objects numpy (array) et shapely (natif, wkb/t) sont 'dumpables'
        # et donc serialisables via Pickle !
        #
        # NUMPY test:
        # ----------
        # >>> import cPickle as pickle
        # >>> import numpy as np
        # >>> np_object = np.asarray([1, 2])
        # >>> pickle.dumps(np_object)
        # "cnumpy.core.multiarray\n_reconstruct\np1\n(cnumpy\nndarray\np2\n(I0\ntS'b'\ntRp3\n(I1\n(I2\ntcnumpy\ndtype\np4\n(S'i8'\nI0\nI1\ntRp5\n(I3\nS'<'\nNNNI-1\nI-1\nI0\ntbI00\nS'\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x02\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\ntb."
        # >>> str_dump_pickle = pickle.dumps(np_object)
        # >>> pickle.loads(str_dump_pickle)
        # array([1, 2])
        #
        # SHAPELY tests:
        # -------------
        # >>> import shapely.geometry as sp_geom
        # >>> import shapely.wkb as sp_wkb
        # >>> point = sp_geom.Point(0, 0)
        # >>> pickle.dumps(point)
        # "cshapely.geometry.point\nPoint\np1\n(tRp2\nS'\\x01\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\nb."
        # >>> pickle.dumps(point.wkb)
        # "S'\\x01\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\n."
        # >>> str_point_wkb = pickle.dumps(point.wkb)
        # >>> pickle.loads(str_point_wkb)
        # '\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        # >>> sp_wkb.loads(pickle.loads(str_point_wkb))
        # <shapely.geometry.point.Point object at 0x7fc00e1ace50>
        # >>> sp_wkb.loads(pickle.loads(str_point_wkb)).wkt
        # 'POINT (0 0)'
        #
        # NAMEDTUPLE:
        # ----------
        # Ya un truc/trick pour le support des namedtuple, le type ou le namedtuple doit etre present
        # dans le contexte de la classe pickler, du coup le namedtuple est initialise a l'exterieur (autre module)
        # on doit s'assurer que le type est accessible. Pour ce faire, j'utilise le contexte globals() de python.
        # Ya une fonction dans imt_tools qui permet de creer un type namedtuple et rajouter en meme temps le type
        # dans le contexte global de python (ya peut etre moyen de faire quelque chose de plus propre avec un contexte
        # a l'echelle du pluging ... a voir)

        dict_states_for_pickle = {
            'dict_edges': self.__dict_edges,
            'dict_lanes': self.__dict_lanes,
            'dict_nodes': self.__dict_nodes,
        }
        return dict_states_for_pickle

    def __setstate__(self, states):
        """

        :param states:
        :return:
        """
        self.pickle_states = states
