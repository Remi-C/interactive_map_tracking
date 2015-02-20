# coding=utf-8
"""Dialog test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = 'remi.cura@gmail.com'
__date__ = '2015-02-20'
__copyright__ = 'Copyright 2015, Lionel Atty, IGN, SIDT'

import unittest

from PyQt4.QtGui import QDialogButtonBox, QDialog

from interactive_map_tracking_dialog import interactive_map_trackingDialog

from utilities import get_qgis_app
QGIS_APP = get_qgis_app()


class interactive_map_trackingDialogTest(unittest.TestCase):
    """Test dialog works."""

    def setUp(self):
        """Runs before each test."""
        self.dialog = interactive_map_trackingDialog(None)

    def tearDown(self):
        """Runs after each test."""
        self.dialog = None

    def test_dialog_ok(self):
        """Test we can click OK."""

        button = self.dialog.button_box.button(QDialogButtonBox.Ok)
        button.click()
        result = self.dialog.result()
        self.assertEqual(result, QDialog.Accepted)

    def test_dialog_cancel(self):
        """Test we can click cancel."""
        button = self.dialog.button_box.button(QDialogButtonBox.Cancel)
        button.click()
        result = self.dialog.result()
        self.assertEqual(result, QDialog.Rejected)

if __name__ == "__main__":
    suite = unittest.makeSuite(interactive_map_trackingDialogTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

