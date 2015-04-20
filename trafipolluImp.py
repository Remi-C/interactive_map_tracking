__author__ = 'atty'

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry

from signalsmanager import SignalsManager
import imt_tools


class TrafiPolluImp(object):
    """

    """

    def __init__(self, iface, dlg):
        """

        """
        self._iface = iface
        self._dlg = dlg
        self._mapCanvas = self._iface.mapCanvas()
        self._signals_manager = SignalsManager.instance()

    def _init_signals_(self):
        """

        """
        self._signals_manager.add_clicked(self._dlg.execute_sql_commands, self.slot_execute_SQL_commands, "GUI")
        self._signals_manager.add_clicked(self._dlg.refreshSqlScriptList, self._slot_refreshSqlScriptList, "GUI")
        self._signals_manager.add(self._dlg.combobox_sql_scripts,
                                  "currentIndexChanged (int)",
                                  self._slot_currentIndexChanged_SQL,
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
        mapCanvas = self._mapCanvas
        mapCanvas_extent = mapCanvas.extent()
        # get the list points from the current extent (from QGIS MapCanvas)
        list_points_from_mapcanvas = imt_tools.construct_listpoints_from_extent(mapCanvas_extent)

        # url: http://qgis.org/api/classQgsMapCanvas.html#af0ffae7b5e5ec8b29764773fa6a74d58
        extent_src_crs = mapCanvas.mapSettings().destinationCrs()
        # url: http://qgis.org/api/classQgsCoordinateReferenceSystem.html#a3cb64f24049d50fbacffd1eece5125ee
        extent_postgisSrid = 932011
        extent_dst_crs = QgsCoordinateReferenceSystem(extent_postgisSrid, QgsCoordinateReferenceSystem.PostgisCrsId)
        # url: http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/crs.html
        xform = QgsCoordinateTransform(extent_src_crs, extent_dst_crs)
        #
        list_points = [xform.transform(point) for point in list_points_from_mapcanvas]

        # list of lists of points
        gPolyline = QgsGeometry.fromPolyline(list_points)
        gPolylineWkt = gPolyline.exportToWkt()

        dict_parameters = {
            'gPolylineWkt': gPolylineWkt,
            'extent_postgisSrid': extent_postgisSrid,
        }

        print "* list_points_from_mapcanvas: ", list_points_from_mapcanvas
        print ""
        print "* gPolygonWkt: ", gPolylineWkt
        print ""
        print "* extent_postgisSrid: ", extent_postgisSrid
        print "* extent_src_crs.postgisSrid: ", extent_src_crs.postgisSrid()
        print ""

        import psycopg2

        connection = psycopg2.connect(database="bdtopo_topological",
                                      dbname="street_gen_3",
                                      user="streetgen", password="streetgen",
                                      host="172.16.3.50")

        cursor = connection.cursor()

        fd = open(imt_tools.get_itemData(self._dlg.combobox_sql_scripts))
        sqlFile = fd.read()
        fd.close()

        self._dlg.plainTextEdit_sql_script.setPlainText(sqlFile)

        # all SQL commands (split on ';')
        sqlCommands = sqlFile.split(';')

        # Execute every command from the input file
        for command in sqlCommands:
            # This will skip and report errors
            # For example, if the tables do not yet exist, this will skip over
            # the DROP TABLE commands
            try:
                # command = command.format(gPolylineWkt, extent_postgisSrid)
                # https://docs.python.org/2/library/string.html#string.Formatter
                # todo : look here for more advanced features on string formatter
                # command = command.format(**dict_parameters)

                if not command.isspace():
                    print "## command_sql: ", command
                    # url: http://initd.org/psycopg/docs/usage.html#query-parameters
                    # url: http://initd.org/psycopg/docs/advanced.html#adapting-new-types
                    cursor.execute(command, dict_parameters)
                    try:
                        tuples = cursor.fetchall()
                        print "=> len(tuples): ", len(tuples)
                        for tuple in tuples:
                            print
                            for element in tuple:
                                print element
                    except:
                        print "commit to Sql Server"
                        connection.commit()
            except psycopg2.OperationalError, msg:
                print "Command skipped: ", msg

        cursor.close()
        connection.close()

    def _slot_refreshSqlScriptList(self):
        """

        """

        self._dlg.combobox_sql_scripts.clear()

        import os

        path = os.path.normcase(os.path.dirname(__file__))
        files = os.listdir(path)

        [
            self._dlg.combobox_sql_scripts.addItem(os.path.basename(i)[:-4], path + '/' + i)
            for i in files if i.endswith('.sql')
        ]

    def _slot_currentIndexChanged_SQL(self, id_index):
        """

        :param id_index:
        """
        sqlFile = ""
        fd = None
        try:
            fd = open(imt_tools.get_itemData(self._dlg.combobox_sql_scripts))
            if fd:
                sqlFile = fd.read()
                fd.close()
        except:
            sqlFile = "Error ! Can't read the SQL file"

        self._dlg.plainTextEdit_sql_script.setPlainText(sqlFile)
