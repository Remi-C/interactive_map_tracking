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
    NAMEDTUPLE_QOBJECT_SIGNAL = namedtuple('TP_NAMEDTUPLE_QOBJECT_SIGNAL',
                                           ['qobject', 'signal_signature'])
    #
    dict_actions = {}

    @staticmethod
    def _build_key_(qobject, signal_signature):
        """

        :param qobject:
        :param signal_signature:
        :return:

        """
        return AbstractSignalsManagerWithSingletonPattern.NAMEDTUPLE_QOBJECT_SIGNAL(qobject, signal_signature)

    def _action_with_test_(self, kwargs):
        """

        :param kwargs:
        :return:
        """
        #
        return_state = 1
        #
        key = kwargs['key']  # key build with qobject + signature
        if key in self.dict_signals.keys():
            kwargs['dict_values'] = self.dict_signals[key]
            #
            if kwargs['func_test_action'](kwargs):
                # already connected
                return_state = -2
            else:
                # perform connection
                kwargs['func_perform_action'](kwargs)
        else:
            # signal doesn't exist
            return_state = -1
        #
        return return_state

    def _action_with_key_(self, kwargs):
        """

        :param kwargs:
        :return:
        """
        #
        return_state = 1
        #
        key = kwargs['key']
        if key in self.dict_signals.keys():
            kwargs['dict_values'] = self.dict_signals[key]
            # perform action
            kwargs['func_perform_action'](kwargs)
        else:
            # signal doesn't exist
            return_state = -1
        #
        return return_state

    def _action_for_all_(self, kwargs):
        """

        :param action:
        :return:
        """
        action = kwargs['action_for_all']
        for key in self.dict_signals.keys():
            action(key)

    def _action_for_group_with_test_(self, kwargs):
        """

        :param kwargs:
        :return:
        """
        #
        return_state = 1
        #
        s_group = kwargs.setdefault('s_group', "all")
        if s_group == "all":
            kwargs['action_for_all']()
        else:
            # noinspection PyBroadException
            try:
                action_with_key_test = kwargs['action_with_key_test']
                for key in self.dict_signals.keys():
                    if key in self.dict_groups[s_group]:
                        action_with_key_test(kwargs)
            except:
                # print s_group
                return_state = -1
        return return_state

    def _action_for_group_(self, kwargs):
        """

        :param kwargs:
        :return:
        """
        return_state = 1
        #
        s_group = kwargs.setdefault('s_group', "all")
        if s_group == "all":
            self._action_for_all_()
        else:
            # noinspection PyBroadException
            try:
                action_with_key = kwargs['action_with_key']
                for key in self.dict_signals.keys():
                    if key in self.dict_group[s_group]:
                        action_with_key(key)
            except:
                print s_group
                return_state = -1
        #
        return return_state
