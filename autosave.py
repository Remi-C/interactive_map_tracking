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
        self._init_signals()

    def update(self):
        """

        """
        self._update_current_layer()

    def enable(self):
        """

        """
        self._enable_autosave()

    def disable(self):
        """

        """
        self._disable_autosave()

    def get_dlg(self):
        """

        :return:

        """
        return self._get_dlg()

    @staticmethod
    def get_name_slot():
        """

        :return:
        """
        return AutoSaveImp._slot_clicked_checkbox_autosave.__name__

class AutoSave:
    pass
AutoSave = IAutoSave