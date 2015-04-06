__author__ = 'latty'

import itertools
from signalsmanagerImp import *
from PyQt4.QtCore import SIGNAL


# def union_dicts(*dicts):
#     return dict(itertools.chain(*map(lambda dct: list(dct.items()), dicts)))


class ISignalsManagerActionConnect(SignalsManagerActionConnectImp):
    """

    """
    def connect(self, qobject, signal_signature):
        """

        :param qobject:
        :param signal_signature:
        :return:
        """
        return self.connect_with_key_test(self._build_key_(qobject, signal_signature))

    def connect_all(self):
        """

        :return:
        """
        self._action_for_all_({'action_for_all': self.connect_with_key_test})

    def connect_group(self, s_group="all"):
        """

        :param s_group:
        :return:
        """
        return self._action_for_group_with_test_({'action_for_all': self.connect_all,
                                                  'action_with_key_test': self.connect_with_key_test,
                                                  's_group': s_group})


class ISignalsManagerActionDisconnect(SignalsManagerActionDisconnectImp):

    def disconnect(self, qobject, signal_signature):
        """

        :param qobject:
        :param signal_signature:
        :return:
        """
        return self.disconnect_with_key_test(self._build_key_(qobject, signal_signature))

    def disconnect_all(self):
        """

        :return:
        """
        #
        self._action_for_all_({'action_for_all': self.disconnect_with_key_test})

    def disconnect_group(self, s_group="all"):
        """

        :param s_group:
        :return:
        """
        return self._action_for_group_with_test_({'action_for_all': self.disconnect_all,
                                                  'action_with_key_test': self.disconnect_with_key_test,
                                                  's_group': s_group})


class ISignalsManagerActionStart(SignalsManagerActionStartImp):

    def start(self, qobject, interval=0.0):
        """

        :param qobject:
        :param signal_signature:
        :return:
        """
        return self.start_with_key(self._build_key_(qobject, 'timeout ()'), interval)

    def start_all(self, interval=0.0):
        """

        :return:
        """
        #
        self._action_for_all_({'action_for_all': self.start_with_key,
                               'interval': interval})

    def start_group(self, interval=0.0, s_group="all"):
        """

        :param s_group:
        :return:
        """
        return self._action_for_group_with_test_({'action_for_all': self.start_all,
                                                  'action_with_key_test': self.start_with_key_test,
                                                  's_group': s_group,
                                                  'interval': interval})


class ISignalsManagerActionStop(SignalsManagerActionStopImp):
    """

    """
    def stop(self, qobject):
        """

        :param qobject:
        :param signal_signature:
        :return:
        """
        return self.stop_with_key_test(self._build_key_(qobject, 'timeout ()'))

    def stop_all(self):
        """

        :return:
        """
        #
        self._action_for_all_({'action_for_all': self.stop_with_key_test})

    def stop_group(self, s_group="all"):
        """

        :param s_group:
        :return:
        """
        return self._action_for_group_with_test_({'action_for_all': self.stop_all,
                                                  'action_with_key_test': self.stop_with_key_test,
                                                  's_group': s_group})


class ISignalsManager(ISignalsManagerActionConnect,
                      ISignalsManagerActionDisconnect,
                      ISignalsManagerActionStart,
                      ISignalsManagerActionStop):
    """

    """

    def add(self, qobject, signal_signature, slot, s_group="all", b_connect_signal=True):
        """

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
                return_state = self.connect_with_key_test(tupple_signal_slot)
            else:
                return_state = -1
        else:
            #
            signal = SIGNAL(signal_signature)
            #
            if b_connect_signal:
                QObject.connect(qobject, signal, slot)
                #
                return_state = 2
            #
            self.dict_signals[tupple_signal_slot] = {
                'Signal': signal,
                'Slot': slot,
                'Signal_is_connected': b_connect_signal
            }
            #
            self.dict_groups.setdefault(s_group, []).append(tupple_signal_slot)
        #
        return return_state, tupple_signal_slot  # return a tuple

    def add_clicked(self, qobject, slot, s_group="all"):
        """

        :param qobject:
        :param s_group:
        :return:
        """
        # print qobject, slot
        return self.add(qobject, "clicked ()", slot, s_group, True)

    def add_timeout(self, qobject, slot, s_group="all"):
        """

        :param qobject:
        :param slot:
        :param s_group:
        :return:
        """
        return self.add(qobject, "timeout ()", slot, s_group, True)


###################################################################################################


class SignalsManager:
    def __init__(self):
        pass


SignalsManager = ISignalsManager