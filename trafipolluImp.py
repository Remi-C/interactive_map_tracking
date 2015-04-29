__author__ = 'atty'

from signalsmanager import SignalsManager
import imt_tools

from trafipolluImp_SQL import trafipolluImp_SQL


class TrafiPolluImp(object):
    """

    """

    def __init__(self, iface, dlg):
        """

        """
        self.__dlg = dlg
        self._signals_manager = SignalsManager.instance()
        #
        self.module_SQL = trafipolluImp_SQL(iface)

    def _init_signals_(self):
        """

        """
        self._signals_manager.add_clicked(self.__dlg.execute_sql_commands, self.slot_execute_SQL_commands, "GUI")
        self._signals_manager.add_clicked(self.__dlg.refreshSqlScriptList, self.__slot_refreshSqlScriptList, "GUI")
        self._signals_manager.add(self.__dlg.combobox_sql_scripts,
                                  "currentIndexChanged (int)",
                                  self.__slot_currentIndexChanged_SQL,
                                  "GUI")

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
        sqlFile = self.__dlg.plainTextEdit_sql_script.toPlainText()
        sql_choice_combobox = imt_tools.get_itemText(self.__dlg.combobox_sql_scripts)

        self.module_SQL.execute_SQL_commands(sqlFile, sql_choice_combobox)

    def __slot_refreshSqlScriptList(self):
        """

        """

        self.__dlg.combobox_sql_scripts.clear()

        import os

        path = os.path.normcase(os.path.dirname(__file__))
        files = os.listdir(path)

        [
            self.__dlg.combobox_sql_scripts.addItem(os.path.basename(i)[:-4], path + '/' + i)
            for i in files if i.endswith('.sql')
        ]

    def __slot_currentIndexChanged_SQL(self, id_index):
        """

        :param id_index:
        """
        sqlFile = ""
        fd = None
        try:
            fd = open(imt_tools.get_itemData(self.__dlg.combobox_sql_scripts))
            if fd:
                sqlFile = fd.read()
                fd.close()
        except:
            sqlFile = "Error ! Can't read the SQL file"

        self.__dlg.plainTextEdit_sql_script.setPlainText(sqlFile)