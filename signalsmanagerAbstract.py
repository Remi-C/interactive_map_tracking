__author__ = 'atty'

from collections import namedtuple

from singletons import Singleton


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
    def _build_key_(qobject, signal_signature):
        """

        :param qobject:
        :param signal_signature:
        :return:

        """
        return AbstractSignalsManagerWithSingletonPattern.NAMEDTUPLE_QOBJECT_SIGNAL(qobject, signal_signature)

    @staticmethod
    def _apply_func_on_qobject_(func, tuple_qobject_signature, dict_params):
        """

        :param func:
        :param dict_params:
        """
        return func(tuple_qobject_signature.qobject, dict_params['Signal'], dict_params['Slot'])

    def _action_with_test_(self, dict_params):
        """

        :param dict_params:
        :return:
        """
        #
        return_state = 1
        #
        if dict_params['key'] in self.dict_signals.keys():
            key = dict_params['key']  # key build with qobject + signature
            dict_params['dict_values'] = self.dict_signals[key]
            #
            if dict_params['func_test_action'](dict_params):
                # already connected
                return_state = -2
            else:
                # perform connection
                dict_params['func_perform_action'](dict_params)
        else:
            # signal doesn't exist
            return_state = -1
        #
        return return_state

    def _action_with_key_(self, dict_params):
        """

        :param dict_params:
        :return:
        """
        #
        return_state = 1
        #
        key = dict_params['key']
        if key in self.dict_signals.keys():
            dict_params['dict_values'] = self.dict_signals[key]
            # perform action
            dict_params['func_perform_action'](dict_params)
        else:
            # signal doesn't exist
            return_state = -1
        #
        return return_state

    def _action_for_all_(self, dict_params):
        """

        :param action:
        :return:
        """
        action = dict_params['action_for_all']
        for key in self.dict_signals.keys():
            action(key)

    def _action_for_group_with_test_(self, dict_params):
        """

        :param dict_params:
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
                action_with_key_test = dict_params['action_with_key_test']
                for key in self.dict_signals.keys():
                    if key in self.dict_groups[s_group]:
                        action_with_key_test(dict_params)
            except:
                # print s_group
                return_state = -1
        return return_state

    def _action_for_group_(self, dict_params):
        """

        :param dict_params:
        :return:
        """
        return_state = 1
        #
        s_group = dict_params.setdefault('s_group', "all")
        if s_group == "all":
            self._action_for_all_()
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
