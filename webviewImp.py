__author__ = 'atty'

from signalsmanager import SignalsManager
from collections import namedtuple
import os.path
from PyQt4.QtCore import QUrl
from PyQt4.QtWebKit import QWebSettings
import qgis_log_tools

class WebViewImp(object):
    """

    """
    def __init__(self, iface, dlg, qgis_plugins_directory):
        """

        """
        self.__iface = iface
        self.__dlg = dlg
        self.__signals_manager = SignalsManager.instance()

        self.TP_NAMEDTUPLE_WEBVIEW = namedtuple(
            'TP_NAMEDTUPLE_WEBVIEW',
            ['state', 'width', 'height', 'online_url', 'offline_url', 'dlg']
        )

        # very dirty @FIXME @TODO : here is the proper way to do it (from within the class `self.plugin_dir`)
        self.qgis_plugins_directory = qgis_plugins_directory

        self.dict_pages = {}
        # url : http://qt-project.org/doc/qt-4.8/qurl.html
        self.tuple_webview_default = self.TP_NAMEDTUPLE_WEBVIEW('init', 0, 0, QUrl(""), QUrl(""), None)
        #
        self.add_about(dlg=dlg.webView_about)
        self.add_user_doc(dlg=dlg.webView_userdoc)
        #
        self.current_webview_name = ""
        self.current_tab_index = -1
        self.margin_default = 60

    def add_user_doc(self, **kwargs):
        """

        :param kwargs:
        :return:
        """
        str_online_url = "https://github.com/Remi-C/interactive_map_tracking/wiki/[User]-User-Guide"
        str_offline_url = os.path.join(self.qgis_plugins_directory, "gui_doc", "Simplified_User_Guide.htm")
        self.add(
            name="user doc",
            online_url=QUrl(kwargs.setdefault('online_url', str_online_url)),
            offline_url=QUrl(kwargs.setdefault('offline_url', str_offline_url)),
            dlg=kwargs.setdefault('dlg', self.tuple_webview_default.dlg),
        )

    def add_about(self, **kwargs):
        """

        :param kwargs:
        :return:
        """
        str_online_url = "https://github.com/Remi-C/interactive_map_tracking/wiki/[User]-About"
        str_offline_url = os.path.join(self.qgis_plugins_directory, "gui_doc", "About.htm")
        self.add(
            name="about",
            online_url=QUrl(kwargs.setdefault('online_url', str_online_url)),
            offline_url=QUrl(kwargs.setdefault('offline_url',str_offline_url)),
            dlg=kwargs.setdefault('dlg', self.tuple_webview_default.dlg),
        )

    def add(self, **kwargs):
        """

        :param kwargs:
        :return:
        """
        webview_tuple = self.TP_NAMEDTUPLE_WEBVIEW(
            kwargs.setdefault('state', self.tuple_webview_default.state),
            kwargs.setdefault('width', self.tuple_webview_default.width),
            kwargs.setdefault('height', self.tuple_webview_default.height),
            kwargs.setdefault('online_url', self.tuple_webview_default.online_url),
            kwargs.setdefault('offline_url', self.tuple_webview_default.offline_url),
            kwargs.setdefault('dlg', self.tuple_webview_default.dlg),
        )
        webview_name = kwargs.setdefault('name', "")
        self.dict_pages[webview_name] = webview_tuple

    def _get_dlg(self):
        """

        :return:
        """
        return self.__dlg

    def slot_loadFinished(self, ok):
        """

        :param ok:

        """
        self.action_loadFinished(ok)

    def action_loadFinished(self, ok):
        """

        :param ok:
        :return:
        """
        # safe because we stop the listener of this event when we changed the tab
        webview_name = self.current_webview_name
        tuple_webview = self.dict_pages.setdefault(webview_name, self.tuple_webview_default)
        webview_dlg = tuple_webview.dlg
        last_state = tuple_webview.state
        qgis_log_tools.logMessageINFO("#last_state : " + str(last_state))

        if ok:
            # we have loaded a HTML page (offline or online)
            qgis_log_tools.logMessageINFO("## WebView : OK")

            # update the QDiaglog sizes
            dlg = None
            if self.__dlg.IMT_Window_Tabs.currentIndex() == self.webview_index_tab:
                dlg = self.__dlg
            width, height = self.compute_frame_size(webview_dlg.page().currentFrame(),
                                                    dlg,
                                                    self.margin_default)
            # update the tuple for this webview_dlg
            self.dict_pages[webview_name] = self.TP_NAMEDTUPLE_WEBVIEW(
                'online',
                width, height,
                tuple_webview.online_url,
                tuple_webview.offline_url,
                webview_dlg
            )
            #
            qgis_log_tools.logMessageINFO("### width : " + str(width) + " - height : " + str(height))
        else:
            if self.dict_pages[webview_name].state == 'online':
                qgis_log_tools.logMessageINFO(
                    "## WebView : FAILED TO LOAD from " + str(self.dict_pages[webview_name].online_url))  # online_url
            else:
                qgis_log_tools.logMessageINFO(
                    "## WebView : FAILED TO LOAD from " + str(self.dict_pages[webview_name].offline_url))
            #
            if self.dict_pages[webview_name].state != 'offline':  # regular case we failed, but we are going to try again
                self.dict_pages[webview_name] = self.TP_NAMEDTUPLE_WEBVIEW(
                    'offline',
                    tuple_webview.width, tuple_webview.height,
                    tuple_webview.online_url,
                    tuple_webview.offline_url,
                    webview_dlg
                )
                # try to load the offline version (still in initial state)
                # @FIXME : doesn't load the images in offline mode on XP...
                webview_dlg.load(QUrl(tuple_webview.offline_url))
            else:  # we already failed last, time, stopping to try
                qgis_log_tools.logMessageINFO("## WebView : stopping to try to retrieve html")

    def load(self, **kwargs):
        # webview_name, index_tab=-1, margin=60
        """

        :param webview_name:
        :param margin:
        :return:
        """
        #
        webview_name = kwargs.setdefault('name', "")
        margin = kwargs.setdefault('margin', self.margin_default)
        index_tab = kwargs.setdefault('index_tab', -1)
        #
        tuple_webview = self.dict_pages.setdefault(webview_name, self.tuple_webview_default)

        webview_dlg = tuple_webview.dlg

        self.margin_default = margin
        self.current_webview_name = webview_name
        self.webview_index_tab = index_tab

        # reset/clear the web widget
        # url : http://qt-project.org/doc/qt-4.8/qwebview.html#settings
        web_setting = webview_dlg.settings()
        web_setting.clearMemoryCaches()
        web_setting.setAttribute(QWebSettings.PluginsEnabled, True)

        global_settings = web_setting.globalSettings()
        #
        global_settings.clearMemoryCaches()
        # Enables plugins in Web pages (e.g. using NPAPI).
        # url: http://doc.qt.io/qt-4.8/qwebsettings.html#WebAttribute-enum
        global_settings.setAttribute(QWebSettings.PluginsEnabled, True)

        # signal : 'loadFinished(bool)'
        self.__signals_manager.add(tuple_webview.dlg,
                                 "loadFinished (bool)",
                                 self.slot_loadFinished,
                                 "WEB")

        if tuple_webview.state == 'offline':  # offline
            webview_dlg.load(tuple_webview.offline_url)
        else:  # 'init' or 'online'
            webview_dlg.load(tuple_webview.online_url)

    @staticmethod
    def compute_frame_size(frame, dlg=None, margin_width=60):
        """

        :param dlg:
        :param frame:
        :param margin_width:
        :return:
        """
        try:
            width = frame.contentsSize().width()
            height = frame.contentsSize().height()
            #
            width += margin_width
            #
            width = max(1024, width)
            height = min(768, max(height, width * 4 / 3))
            #
            try:
                dlg.resize(width, height)
            except:
                pass
            finally:
                return width, height
        except:
            pass

    @staticmethod
    def update_size_dlg_from_tuple(dlg, param_tuple):
        """

        :param dlg:
        :param param_tuple:
        :return:
        """
        try:
            dlg.resize(param_tuple.width, param_tuple.height)
        except:
            pass
        finally:
            return param_tuple.width, param_tuple.height
