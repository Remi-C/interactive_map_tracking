__author__ = 'latty'

from PyQt4.QtCore import SIGNAL
#
from signalsmanager_actions import ISignalsManagerActionConnect
from signalsmanager_actions import ISignalsManagerActionDisconnect
from signalsmanager_actions import ISignalsManagerActionStart
from signalsmanager_actions import ISignalsManagerActionStop


class ISignalsManager(ISignalsManagerActionConnect,
                      ISignalsManagerActionDisconnect,
                      ISignalsManagerActionStart,
                      ISignalsManagerActionStop):
    """

    """

    def add(self, qobject, signal_signature, slot, s_group="all", b_connect_signal=True):
        """
        Generic version to add a Qt signal into our manager

        :param qobject:
        :param signal_signature:
        :param slot:
        :param b_connect_signal:
        :return:

        """
        return_state = 1
        #
        tupple_signal_slot = self._build_key_(qobject, signal_signature)
        #
        if tupple_signal_slot in self.dict_signals.keys():
            if b_connect_signal:
                return_state = self._connect_with_key_test_(tupple_signal_slot)
            else:
                return_state = -1
        else:
            #
            signal = SIGNAL(signal_signature)
            #
            self.dict_signals[tupple_signal_slot] = {
                'Signal': signal,
                'Slot': slot
            }
            #
            self.dict_groups.setdefault(s_group, []).append(tupple_signal_slot)
            #
            if b_connect_signal:
                if self._connect_with_key_(tupple_signal_slot):
                    return_state = 2
        #
        return return_state, tupple_signal_slot  # return a tuple

    def add_clicked(self, qobject, slot, s_group="all"):
        """
        Add a specific signal 'clicked' (from Qt GUI) into our manager

        :param qobject:
        :param s_group:
        :return:
        """
        # print qobject, slot
        return self.add(qobject, "clicked ()", slot, s_group, True)

    def add_timeout(self, qobject, slot, s_group="all"):
        """
        Add a specific signal 'timeout' (for QTimer) into our manager

        :param qobject:
        :param slot:
        :param s_group:
        :return:
        """
        return self.add(qobject, "timeout ()", slot, s_group, True)

    def get_slot(self, qobject, signal_signature):
        """

        :param qobject:
        :param signal_signature:
        :return:
        """
        return_slot = None
        tupple_signal_slot = self._build_key_(qobject, signal_signature)
        if tupple_signal_slot in self.dict_signals.keys():
            return_slot = self.dict_signals[tupple_signal_slot]['Slot']
        return return_slot


###################################################################################################


class SignalsManager:
    def __init__(self):
        pass


SignalsManager = ISignalsManager