__author__ = 'latty'

from PyQt4.QtCore import QSettings


class DecoratorsForQt(object):
    """

    """
    _dict_obj_ = {}

    @staticmethod
    def save_checked_state(group_name):
        """

        :param group_name:
        :return:
        """

        def __decorated_qt_slots(func):
            """

            :param func:
            :return:
            """
            def __save_state(dlg, dict_qobj):
                """

                """
                qobj_sender = dlg.sender()
                if qobj_sender:
                    key = func.__name__  # slot name function
                    #
                    dict_qobj[key] = qobj_sender
                    #
                    s = QSettings()
                    s.beginGroup(group_name)
                    s.setValue(key, bool(qobj_sender.isChecked()))
                    s.endGroup()
                    #
                    # print "* dictionnary: " + str(dict_qobj)

            def __wrapper(*args, **kwargs):
                """

                :param args:
                :param kwargs:
                :return:
                """
                # pre
                __save_state(args[0].get_dlg(), DecoratorsForQt._dict_obj_)
                #
                func(*args, **kwargs)

            return __wrapper

        return __decorated_qt_slots

