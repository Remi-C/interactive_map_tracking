__author__ = 'atty'

from autosaveImp import AutoSaveImp


class IAutoSave(AutoSaveImp):
    """

    """
    def __init__(self, iface, dlg):
        """

        """
        super(IAutoSave, self).__init__(iface, dlg)

    def init(self):
        """

        """
        self._init_signals_()

    def update(self):
        """

        """
        self._update_current_layer_()

    def enable(self):
        """

        """
        self._enable_autosave_()

    def disable(self):
        """

        """
        self._disable_autosave_()


class AutoSave:
    pass
AutoSave = IAutoSave