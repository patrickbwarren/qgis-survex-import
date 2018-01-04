# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SurvexImport
                                 A QGIS plugin
 Import features from survex .3d files
                             -------------------
        begin                : 2018-01-03
        copyright            : (C) 2018 by Patrick B Warren
        email                : patrickbwarren@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load SurvexImport class from file SurvexImport.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .survex_import import SurvexImport
    return SurvexImport(iface)
