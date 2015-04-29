__author__ = 'atty'

from trafipolluImp import TrafiPolluImp


class ITrafiPollu(TrafiPolluImp):
    """

    """

    def __init__(self, iface, dlg):
        """

        """
        super(ITrafiPollu, self).__init__(iface, dlg)

    def init(self):
        """

        """
        self._init_signals_()

    def update(self):
        """

        """
        pass

    def enable(self):
        """

        """
        self._enable_trafipollu_()

    def disable(self):
        """

        """
        self._disable_trafipollu_()

    def get_dlg(self):
        """

        :return:

        """
        return self.__dlg


class TrafiPollu:
    pass


TrafiPollu = ITrafiPollu