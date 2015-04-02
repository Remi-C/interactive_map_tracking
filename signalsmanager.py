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


class AbstractSignalsManagerWithSingletonPattern(Singleton):
    """

    """
    # STATIC(s)
    dict_signals = {}
    dict_groups = {}
    #
    NAMEDTUPLE_QOBJECT_SIGNAL = namedtuple('TP_NAMEDTUPLE_QOBJECT_SIGNAL', ['qobject', 'signal_signature'])
    #
    dict_actions = {}

    @staticmethod
    def _initialize_():
        """

        """
        pass

    @classmethod
    def getInstance(cls):
        """

        :param args:
        :param kargs:
        :return:
        """
        return super(AbstractSignalsManagerWithSingletonPattern, cls).instance()

    @staticmethod
    def build_key(qobject, signal_signature):
        """

        :param qobject:
        :param signal_signature:
        :return:

        """
        return AbstractSignalsManagerWithSingletonPattern.NAMEDTUPLE_QOBJECT_SIGNAL(qobject, signal_signature)

    @staticmethod
    def _helper_qobject_params_(func, key, dict_params):
        """

        :param func:
        :param dict_params:
        """
        return func(key.qobject, dict_params['Signal'], dict_params['Slot'])

    def action_with_key_test(self, dict_params):
        """

        :param dict_params:
        :return:
        """
        #
        return_state = 1
        #
        if dict_params['key'] in self.dict_signals.keys():
            dict_params['dict_values'] = self.dict_signals[dict_params['key']]
            #
            if dict_params['func_test_action'](self, dict_params):
                # already connected
                return_state = -2
            else:
                #
                dict_params['func_perform_action'](self, dict_params)
        else:
            # signal doesn't exist
            return_state = -1
        #
        return return_state

    def action_with_key(self, dict_params):
        """

        :param dict_params:
        :return:
        """
        #
        return_state = 1
        #
        if dict_params['key'] in self.dict_signals.keys():
            dict_params['dict_values'] = self.dict_signals[dict_params['key']]
            #
            dict_params['func_perform_action'](self, dict_params)
        else:
            # signal doesn't exist
            return_state = -1
        #
        return return_state

    def action_for_all(self, dict_params):
        """

        :param action:
        :return:
        """
        action = dict_params['action_for_all']
        for key in self.dict_signals.keys():
            action(key)

    def action_for_group_with_test(self, dict_params):
        """

        :param s_group:
        :return:
        """
        #
        return_state = 1
        #
        s_group = dict_params.setdefault('s_group', "all")
        if s_group == "all":
            dict_params['action_for_all']()
        else:
            # noinspection PyBroadException
            try:
                #
                action_with_key_test = dict_params['action_with_key_test']
                for key in self.dict_signals.keys():
                    if key in self.dict_groups[s_group]:
                        action_with_key_test(dict_params)
            except:
                print s_group
                return_state = -1
        #
        return return_state

    def action_for_group(self, dict_params):
        """
        """
        #
        return_state = 1
        #
        s_group = dict_params.setdefault('s_group', "all")
        if s_group == "all":
            self.action_for_all()
        else:
            # noinspection PyBroadException
            try:
                action_with_key = dict_params['action_with_key']
                for key in self.dict_signals.keys():
                    if key in self.dict_group[s_group]:
                        action_with_key(key)
            except:
                print s_group
                return_state = -1
        #
        return return_state


# ##################################################################################################

class SignalsManagerActionConnectImp(AbstractSignalsManagerWithSingletonPattern):
    """

    """

    def action_connect_test_reject(self, dict_params):
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
        #
        self._helper_qobject_params_(QObject.connect, key, dict_values)
        #
        dict_values['Signal_is_connected'] = True

    AbstractSignalsManagerWithSingletonPattern.dict_actions['connect'] = {
        'func_test_action': action_connect_test_reject,
        'func_perform_action': action_connect_perform}


class ISignalsManagerActionConnect(SignalsManagerActionConnectImp):
    # ###############################################
    def connect_with_key_test(self, key):
        """

        :param key:
        :return:
        """
        action_connect = self.dict_actions['connect']
        return self.action_with_key_test({'key': key,
                                          'func_test_action': action_connect['func_test_action'],
                                          'func_perform_action': action_connect['func_perform_action']})

    def connect(self, qobject, signal_signature):
        """

        :param qobject:
        :param signal_signature:
        :return:
        """
        return self.connect_with_key_test(self.build_key(qobject, signal_signature))

    def connect_all(self):
        """

        :return:
        """
        self.action_for_all({'action_for_all': self.connect_with_key_test})

    def connect_group(self, s_group="all"):
        """

        :param s_group:
        :return:
        """
        return self.action_for_group_with_test({'action_for_all': self.connect_all,
                                                'action_with_key_test': self.connect_with_key_test,
                                                's_group': s_group})


class SignalsManagerActionDisconnectImp(AbstractSignalsManagerWithSingletonPattern):
    """

    """
    ################################################
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
        #
        self._helper_qobject_params_(QObject.disconnect, key, dict_values)
        #
        dict_values['Signal_is_connected'] = False

    #
    AbstractSignalsManagerWithSingletonPattern.dict_actions['disconnect'] = {
        'func_test_action': action_disconnect_test_action,
        'func_perform_action': action_disconnect_perform}


class ISignalsManagerActionDisconnect(SignalsManagerActionDisconnectImp):
    # ###############################################
    def disconnect_with_key_test(self, key):
        """

        :param key:
        :return:
        """
        action_connect = self.dict_actions['disconnect']
        return self.action_with_key_test({'key': key,
                                          'func_test_action': action_connect['func_test_action'],
                                          'func_perform_action': action_connect['func_perform_action']})

    def disconnect(self, qobject, signal_signature):
        """

        :param qobject:
        :param signal_signature:
        :return:
        """
        return self.disconnect_with_key_test(self.build_key(qobject, signal_signature))

    def disconnect_all(self):
        """

        :return:
        """
        #
        self.action_for_all({'action_for_all': self.disconnect_with_key_test})

    def disconnect_group(self, s_group="all"):
        """

        :param s_group:
        :return:
        """
        return self.action_for_group_with_test({'action_for_all': self.disconnect_all,
                                                'action_with_key_test': self.disconnect_with_key_test,
                                                's_group': s_group})


class SignalsManagerActionStartImp(AbstractSignalsManagerWithSingletonPattern):
    """

    """
    # ###############################################
    def action_start_test_action(self, dict_params):
        """

        :param dict_params:
        :return:
        """
        # Todo: need specification here
        return False

    def action_start_perform(self, dict_params):
        """

        :param key:
        :param dict_params:
        :return:
        """
        qtimer = dict_params['key'].qobject
        interval = dict_params['interval']
        #
        qtimer.start(interval)

    #
    AbstractSignalsManagerWithSingletonPattern.dict_actions['start'] = {
        'func_test_action': action_start_test_action,
        'func_perform_action': action_start_perform}


class ISignalsManagerActionStart(SignalsManagerActionStartImp):
    ################################################
    def start_with_key(self, key, interval):
        """

        :param key:
        :return:
        """
        action = self.dict_actions['start']
        # return self.action_with_key_test(key, action['func_test_action'], action['func_perform_action'])
        return self.action_with_key_test({'key': key,
                                          'func_test_action': action['func_test_action'],
                                          'func_perform_action': action['func_perform_action'],
                                          'interval': interval})

    def start(self, qobject, interval=0.0):
        """

        :param qobject:
        :param signal_signature:
        :return:
        """
        return self.start_with_key(self.build_key(qobject, 'timeout ()'), interval)

    def start_all(self, interval=0.0):
        """

        :return:
        """
        #
        self.action_for_all({'action_for_all': self.start_with_key,
                             'interval': interval})

    def start_group(self, interval=0.0, s_group="all"):
        """

        :param s_group:
        :return:
        """
        return self.action_for_group_with_test({'action_for_all': self.start_all,
                                                'action_with_key_test': self.start_with_key_test,
                                                's_group': s_group,
                                                'interval': interval})


class SignalsManagerActionStopImp(AbstractSignalsManagerWithSingletonPattern):
    """

    """
    ################################################
    def action_stop_test_action(self, dict_params):
        """

        :param dict_params:
        :return:
        """
        qtimer = dict_params['key'].qobject
        return not qtimer.isActive()

    def action_stop_perform(self, dict_params):
        """

        :param key:
        :param dict_params:
        :return:
        """
        qtimer = dict_params['key'].qobject
        #
        qtimer.stop()

    #
    AbstractSignalsManagerWithSingletonPattern.dict_actions['stop'] = {
        'func_test_action': action_stop_test_action,
        'func_perform_action': action_stop_perform}


class ISignalsManagerActionStop(SignalsManagerActionStopImp):
    # ###############################################
    def stop_with_key_test(self, key):
        """

        :param key:
        :return:
        """
        action = self.dict_actions['stop']
        return self.action_with_key_test({'key': key,
                                          'func_test_action': action['func_test_action'],
                                          'func_perform_action': action['func_perform_action']})

    def stop(self, qobject):
        """

        :param qobject:
        :param signal_signature:
        :return:
        """
        return self.stop_with_key_test(self.build_key(qobject, 'timeout ()'))

    def stop_all(self):
        """

        :return:
        """
        #
        self.action_for_all({'action_for_all': self.stop_with_key_test})

    def stop_group(self, s_group="all"):
        """

        :param s_group:
        :return:
        """
        return self.action_for_group_with_test({'action_for_all': self.stop_all,
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
        key = self.build_key(qobject, signal_signature)
        #
        if key in self.dict_signals.keys():
            if b_connect_signal:
                return_state = self.connect_with_key_test(key)
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
        return return_state, key  # return a tuple

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