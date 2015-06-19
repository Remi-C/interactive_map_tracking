__author__ = 'atty'

from trackingpositionImp import TrackingPositionImp


class ITrackingPosition(TrackingPositionImp):
    """

    """
    def __init__(self, iface, dlg):
        """

        """
        super(ITrackingPosition, self).__init__(iface, dlg)

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
        pass

    def disable(self):
        """

        """
        pass

    def get_dlg(self):
        """

        :return:

        """
        return self.dlg


# class AutoSave:
#     pass
TrackingPosition = ITrackingPosition