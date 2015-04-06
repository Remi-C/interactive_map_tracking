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
        self.init_signals()

    def update(self):
        """

        """
        self.update_current_layer()

    def enable(self):
        """

        """
        self.enable_autosave()

    def disable(self):
        """

        """
        self.disable_autosave()


class AutoSave:
    pass
AutoSave = IAutoSave