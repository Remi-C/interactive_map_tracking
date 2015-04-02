__author__ = 'latty'

from PyQt4.QtCore import QObject, SIGNAL

###################################################################################################
from singletons import SingletonDecorator


class SignalsManager_with_Decorator_Pattern(object):
    """

    """
    def __init__(self):
        pass

SignalsManager_with_Decorator_Pattern = SingletonDecorator(SignalsManager_with_Decorator_Pattern)

###################################################################################################
from singletons import Borg


class SignalsManager_with_Borg_Pattern(object, Borg):
    """

    """
    # def __init__(self):
    #     #
    #     self.dict_signals = {}
    #
    def add_signal(self, qobject, signal_signature, slot, b_connect_signal=True):
        """

        :param qobject:
        :param signal_signature:
        :param slot:

        """
        #
        if qobject in self.dict_signals:
            return -1
        #
        if b_connect_signal:
            QObject.connect(qobject, SIGNAL(signal_signature), slot)
        #
        # self.dict_signals[qobject] = [signal_signature, slot, b_connect_signal]

###################################################################################################
from singletons import Unique


class SignalsManager_with_Unique_Pattern(Unique):
    def __init__(self):
        self.dict_signals = {}
    def add_signal(self, qobject, signal_signature, slot, b_connect_signal=True):
        """

        :param qobject:
        :param signal_signature:
        :param slot:

        """
        #
        if qobject in self.dict_signals:
            return -1
        #
        if b_connect_signal:
            QObject.connect(qobject, SIGNAL(signal_signature), slot)
        #
        self.dict_signals[qobject] = [signal_signature, slot, b_connect_signal]
#

###################################################################################################
from singletons import Singleton
from collections import namedtuple


class SignalsManager_with_Singleton_Pattern_Abstract(Singleton):
    """

    """
    # STATIC(s)
    dict_signals = {}
    dict_groups = {}

    #
    NAMEDTUPLE_QOBJECT_SIGNAL = namedtuple('TP_NAMEDTUPLE_QOBJECT_SIGNAL', ['qobject', 'signal_signature'])

    @staticmethod
    def _initialize_():
        """

        """
        # print "_initialize_ from 'SignalsManager_with_Singleton_Pattern'"
        pass

    # def getInstance(cls, *args, **kargs):
    @classmethod
    def getInstance(cls):
        """

        :param args:
        :param kargs:
        :return:
        """
        # return super(SignalsManager_with_Singleton_Pattern, cls).getInstance(cls, *args, **kargs)
        return super(SignalsManager_with_Singleton_Pattern_Abstract, cls).getInstance()

    @staticmethod
    def build_key(qobject, signal_signature):
        """

        :param qobject:
        :param signal_signature:
        :return:

        """
        return SignalsManager_with_Singleton_Pattern_Abstract.NAMEDTUPLE_QOBJECT_SIGNAL(qobject, signal_signature)

    @staticmethod
    def _helper_qobject_params_(func, key, dict_params):
        """

        :param func:
        :param dict_params:
        """
        return func(key.qobject, dict_params['Signal'], dict_params['Slot'])

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
        key = self.build_key(qobject, signal_signature)
        #
        if key in self.dict_signals.keys():
            if b_connect_signal:
                return_state = self.connect_with_key(key)
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
            self.dict_signals[key] = {
                'Signal': signal,
                'Slot': slot,
                'Signal_is_connected': b_connect_signal
            }
            #
            self.dict_groups.setdefault(s_group, []).append(key)
        #
        return return_state, key    # return a tuple

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

    def action_with_key(self, key, func_test_action, func_perform_action):
        """

        :param key:
        :param s_param:
        :param func:
        :return:
        """
        #
        return_state = 1
        #
        if key in self.dict_signals.keys():
            #
            dict_values = self.dict_signals[key]
            #
            dict_params = {'key': key, 'dict_values': dict_values}
            #
            if func_test_action(self, dict_params):
                # already connected
                return_state = -2
            else:
                #
                func_perform_action(self, dict_params)
        else:
            # signal doesn't exist
            return_state = -1
        #
        return return_state

    def action_connect_test_action(self, dict_params):
        """

        :param dict_params:
        :return:
        """
        dict_values = dict_params['dict_values']
        return dict_values['Signal_is_connected']

    def action_connect_perform(self, dict_params):
        """

        :param key:
        :param dict_params:
        :return:
        """
        key = dict_params['key']
        dict_values = dict_params['dict_values']
        self._helper_qobject_params_(QObject.connect, key, dict_values)

    def action_disconnect_test_action(self, dict_params):
        """

        :param dict_params:
        :return:
        """
        dict_values = dict_params['dict_values']
        return not dict_values['Signal_is_connected']

    def action_disconnect_perform(self, dict_params):
        """

        :param key:
        :param dict_params:
        :return:
        """
        key = dict_params['key']
        dict_values = dict_params['dict_values']
        self._helper_qobject_params_(QObject.disconnect, key, dict_values)

    dict_actions = {
        'connect': {'func_test_action': action_connect_test_action,
                    'func_perform_action': action_connect_perform},
        'disconnect': {'func_test_action': action_disconnect_test_action,
                       'func_perform_action': action_disconnect_perform}
    }

    def action_for_all(self, action):
        """

        :param action:
        :return:
        """
        for key in self.dict_signals.keys():
            action(key)

    def action_for_group(self, action_for_all, action_with_key, s_group="all"):
        """

        :param s_group:
        :return:
        """
        #
        return_state = 1
        #
        if s_group == "all":
            self.action_for_all()
        else:
            # noinspection PyBroadException
            try:
                #
                for key in self.dict_groups[s_group]:
                    self.action_with_key(key)
            except:
                return_state = -1
        #
        return return_state

###################################################################################################


class SignalsManager_with_Singleton_Pattern_Imp(SignalsManager_with_Singleton_Pattern_Abstract):
    """

    """

    ################################################
    def connect_with_key(self, key):
        """

        :param key:
        :return:
        """
        action_connect = self.dict_actions['connect']
        return self.action_with_key(key, action_connect['func_test_action'], action_connect['func_perform_action'])

    def connect(self, qobject, signal_signature):
        """

        :param qobject:
        :param signal_signature:
        :return:
        """
        return self.connect_with_key(self.build_key(qobject, signal_signature))

    def connect_all(self):
        """

        :return:
        """
        self.action_for_all(self.connect_with_key)

    def connect_group(self, s_group="all"):
        """

        :param s_group:
        :return:
        """
        return self.action_for_group(self.connect_all, self.connect_with_key, s_group)

    ################################################

    def disconnect_with_key(self, key):
        """

        :param key:
        :return:
        """
        action_connect = self.dict_actions['disconnect']
        return self.action_with_key(key, action_connect['func_test_action'], action_connect['func_perform_action'])

    def disconnect(self, qobject, signal_signature):
        """

        :param qobject:
        :param signal_signature:
        :return:
        """
        return self.disconnect_with_key(self.build_key(qobject, signal_signature))

    def disconnect_all(self):
        """

        :return:
        """
        #
        self.action_for_all(self.disconnect_with_key)

    def disconnect_group(self, s_group="all"):
        """

        :param s_group:
        :return:
        """
        return self.action_for_group(self.disconnect_all, self.disconnect_with_key, s_group)


###################################################################################################


class SignalsManager:
    def __init__(self):
        pass

SignalsManager = SignalsManager_with_Singleton_Pattern_Imp