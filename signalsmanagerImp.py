__author__ = 'atty'

from PyQt4.QtCore import QObject

from signalsmanagerAbstract import AbstractSignalsManagerWithSingletonPattern


# ##################################################################################################
class SignalsManagerActionConnectImp(AbstractSignalsManagerWithSingletonPattern):
    """

    """
    #
    id_str_signal_is_connected = 'signal_is_connected'
    # ! LAMBDA FUNCTIONS !
    # LAMBDA with multiple statements
    # url:
    # - http://stackoverflow.com/questions/862412/is-it-possible-to-have-multiple-statements-in-a-python-lambda-expression
    # - http://www.tutorialspoint.com/python/dictionary_update.htm
    AbstractSignalsManagerWithSingletonPattern.dict_actions['connect'] = {
        'func_test_action': lambda x: x['dict_values'].setdefault(
            SignalsManagerActionConnectImp.id_str_signal_is_connected, False),
        'func_perform_action': lambda x: [
            QObject.connect(x['key'].qobject, x['dict_values']['Signal'], x['dict_values']['Slot']),
            x['dict_values'].__setitem__(SignalsManagerActionConnectImp.id_str_signal_is_connected, True)
        ]
    }

    # ###############################################
    def _connect_with_key_test_(self, key):
        """

        :param key:
        :return:
        """
        action_connect = self.dict_actions['connect']
        return self._action_with_test_(
            {
                'key': key,
                'func_test_action': action_connect['func_test_action'],
                'func_perform_action': action_connect['func_perform_action']
            }
        )

    def _connect_with_key_(self, key):
        """

        :param key:
        :return:
        """
        action_connect = self.dict_actions['connect']
        return self._action_with_key_(
            {
                'key': key,
                'func_perform_action': action_connect['func_perform_action']
            }
        )


# ##################################################################################################
class SignalsManagerActionDisconnectImp(AbstractSignalsManagerWithSingletonPattern):
    """

    """
    AbstractSignalsManagerWithSingletonPattern.dict_actions['disconnect'] = {
        'func_test_action': lambda x: not x['dict_values'].setdefault(
            SignalsManagerActionConnectImp.id_str_signal_is_connected, False),
        'func_perform_action': lambda x:
        [
            QObject.disconnect(x['key'].qobject, x['dict_values']['Signal'], x['dict_values']['Slot']),
            x['dict_values'].__setitem__(SignalsManagerActionConnectImp.id_str_signal_is_connected, False)
        ]
    }

    # ##############################################
    def _disconnect_with_key_test_(self, key):
        """

        :param key:
        :return:
        """
        action_disconnect = self.dict_actions['disconnect']
        return self._action_with_test_(
            {
                'key': key,
                'func_test_action': action_disconnect['func_test_action'],
                'func_perform_action': action_disconnect['func_perform_action']
            }
        )


# ##################################################################################################
class SignalsManagerActionStartImp(AbstractSignalsManagerWithSingletonPattern):
    """

    """
    AbstractSignalsManagerWithSingletonPattern.dict_actions['start'] = {
        'func_test_action': lambda x: False,    # no condition to start a thread (?)
        'func_perform_action': lambda x: x['key'].qobject.start(x['interval'])
    }

    ################################################
    def _start_with_key_(self, key, interval):
        """

        :param key:
        :return:
        """
        action = self.dict_actions['start']
        return self._action_with_test_(
            {
                'key': key,
                'func_test_action': action['func_test_action'],
                'func_perform_action': action['func_perform_action'],
                'interval': interval
            }
        )


# ##################################################################################################
class SignalsManagerActionStopImp(AbstractSignalsManagerWithSingletonPattern):
    """

    """
    AbstractSignalsManagerWithSingletonPattern.dict_actions['stop'] = {
        'func_test_action': lambda x: not x['key'].qobject.isActive(),
        'func_perform_action': lambda x: x['key'].qobject.stop()
    }

    # ###############################################
    def _stop_with_key_test_(self, key):
        """

        :param key:
        :return:
        """
        action = self.dict_actions['stop']
        return self._action_with_test_(
            {
                'key': key,
                'func_test_action': action['func_test_action'],
                'func_perform_action': action['func_perform_action']
            }
        )