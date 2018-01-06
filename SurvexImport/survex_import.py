# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SurvexImport
                                 A QGIS plugin
 Import features from survex .3d files
                              -------------------
        begin                : 2018-01-03
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Patrick B Warren
        email                : patrickbwarren@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from survex_import_dialog import SurvexImportDialog
import os.path

from qgis.core import *
from PyQt4.QtCore import QVariant

from osgeo.osr import SpatialReference

from os import unlink
from re import search
from tempfile import NamedTemporaryFile
from subprocess import Popen, PIPE
import platform

class SurvexImport:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SurvexImport_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Import .3d file')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'SurvexImport')
        self.toolbar.setObjectName(u'SurvexImport')

        self.dlg = SurvexImportDialog()
        
        self.dlg.selectedFile.clear()
        self.dlg.fileSelector.clicked.connect(self.select_3d_file)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SurvexImport', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        # self.dlg = SurvexImportDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/SurvexImport/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Import features from .3d files'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Import .3d file'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def select_3d_file(self):
        filename = QFileDialog.getOpenFileName(self.dlg, "Select .3d file ","", '*.3d')
        self.dlg.selectedFile.setText(filename)

    # Functions to deal with .3d CRS, adding legs, and adding stations

    # Extract EPSG number from PROJ.4 string from 3d file using GDAL tools.
    # First try to match an explicit EPSG number, and check this is recognised.
    # If this fails, try to match the entire PROJ.4 string.  The reason for 
    # this somewhat convoluted route is to ensure if there is an EPSG number
    # in the passed argument, it is returned 'as is' and not transmuted
    # into another EPSG number with ostensibly the same CRS.

    def extract_epsg(self, proj4string):
        srs = SpatialReference()
        epsg_match = search('epsg:([0-9]*)', proj4string)
        if epsg_match:
            return_code = srs.ImportFromEPSG(int(epsg_match.group(1)))
        else:
            return_code = srs.ImportFromProj4(proj4string)
        if return_code:
            raise Exception("Invalid proj4 string: %s" % proj4string)
        code = srs.GetAttrValue('AUTHORITY', 1)
        epsg = int(code)
        QgsMessageLog.logMessage("proj4string %s --> EPSG:%i" % (proj4string, epsg),
                                 tag='Import .3d', level=QgsMessageLog.INFO)
        return epsg

    # Add a memory layer with title and geom 'Point' or 'LineString'
    # Note that 'PointZ' and 'LineStringZ' are not possible in QGIS 2.18
    # However the z-dimension data is respected.

    def add_layer(self, title, subtitle, geom, epsg):
        uri = '%s?crs=epsg:%i' % (geom, epsg) if epsg else geom
        name = '%s - %s' % (title, subtitle) if title else subtitle
        layer =  QgsVectorLayer(uri, name, 'memory')
        if not layer.isValid():
            raise Exception("Invalid layer with %s" % uri)
        QgsMessageLog.logMessage("Memory layer '%s' called '%s' added" % (uri, name),
                                 tag='Import .3d', level=QgsMessageLog.INFO)
        return layer

    # Add attributes (fields) for legs

    leg_flags = ['DUPLICATE', 'SPLAY', 'SURFACE']

    def add_leg_fields(self, layer):
        attrs = [QgsField(flag, QVariant.Int) for flag in self.leg_flags]
        layer.dataProvider().addAttributes(attrs)
        layer.updateFields() 

    # Add a leg into the legs layer, style is raided for the attributes
    
    def add_leg(self, layer, xyz_start, xyz_end, style):
        if not layer: return
        xyz_pair = [QgsPointV2(QgsWKBTypes.PointZ, *xyz) for xyz in [xyz_start, xyz_end]]
        attrs = [1 if flag in style else 0 for flag in self.leg_flags]
        linestring = QgsLineStringV2()
        linestring.setPoints(xyz_pair)
        feat = QgsFeature()
        geom = QgsGeometry(linestring)
        feat.setGeometry(geom) 
        feat.setAttributes(attrs)
        layer.dataProvider().addFeatures([feat])

    # Add attributes (fields) for stations

    station_flags = ['SURFACE', 'EXPORTED', 'FIXED', 'ENTRANCE']
        
    def add_station_fields(self, layer):
        attrs = [QgsField(flag, QVariant.Int) for flag in self.station_flags]
        attrs.insert(0, QgsField('NAME', QVariant.String))
        layer.dataProvider().addAttributes(attrs)
        layer.updateFields() 

    # Add a station into the stations layer, using flags as attributes 

    def add_station(self, layer, xyz, name, flags):
        if not layer: return
        attrs = [1 if flag in flags else 0 for flag in self.station_flags]
        attrs.insert(0, name)
        feat = QgsFeature()
        geom = QgsGeometry(QgsPointV2(QgsWKBTypes.PointZ, *xyz))
        feat.setGeometry(geom)
        feat.setAttributes(attrs)
        layer.dataProvider().addFeatures([feat])

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:

            # This is where all the work is done.

            # 'perfection is achieved not when nothing more can be
            # added but when nothing more can be taken away'

            survex3dfile = self.dlg.selectedFile.text()

            include_legs = self.dlg.checkLegs.isChecked()
            include_stations = self.dlg.checkStations.isChecked()

            exclude_surface_legs = not self.dlg.checkLegsSurface.isChecked()
            exclude_splay_legs = not self.dlg.checkLegsSplay.isChecked()
            exclude_duplicate_legs = not self.dlg.checkLegsDuplicate.isChecked()

            exclude_surface_stations = not self.dlg.checkStationsSurface.isChecked()

            get_crs = self.dlg.checkGetCRS.isChecked()

            if not os.path.exists(survex3dfile):
                raise Exception("File '%s' doesn't exist" % survex3dfile)

            # Run dump3d and slurp the output (note currently stderr is unused)
            # First, try to figure out where the executable is.

            # TO BE DONE: for MAC OS X add 'Darwin' : '...' option in here...

            dump3d_dict = {'Linux' : '/usr/bin/dump3d',
                           'Windows' : 'C:\Program Files (x86)\Survex\dump3d.exe'}

            try:
                dump3d_exe = dump3d_dict[platform.system()]
            except KeyError:
                raise Exception("Unrecognised system '%s'" % platform.system())

            if not os.path.exists(dump3d_exe):
                raise Exception("Executable '%s' doesn't exist" % dump3d_exe)

            p = Popen([dump3d_exe, survex3dfile], stdout=PIPE, stderr=PIPE)

            dump3d_out, dump3d_err = p.communicate()

            if p.returncode:
                for line in dump3d_out.splitlines():
                    QgsMessageLog.logMessage(line, tag='Import .3d', level=QgsMessageLog.CRITICAL)
                raise Exception("dump3d failed, see log for details")

            # Now parse the dump3d output
    
            leg_layer, station_layer = None, None
            
            title, epsg = None, None

            # We run this like a gawk /pattern/ { action } script
    
            for line in dump3d_out.splitlines():

                fields = line.split()
            
                if fields[0] == 'TITLE':
                    title = ' '.join(fields[1:]).strip('"')

                if get_crs and fields[0] == 'CS':
                    proj4string = ' '.join(fields[1:])
                    epsg = self.extract_epsg(proj4string)

                if fields[0] == 'MOVE':
                    xyz_start = [float(v) for v in fields[1:4]]
        
                if include_legs and fields[0] == 'LINE': 
                    xyz_end = [float(v) for v in fields[1:4]]
                    style = ' '.join(fields[5:])
                    if not leg_layer:
                        leg_layer = self.add_layer(title, 'legs', 'LineString', epsg)
                        self.add_leg_fields(leg_layer)
                    while (True):
                        if exclude_surface_legs and 'SURFACE' in style: break
                        if exclude_splay_legs and 'SPLAY' in style: break
                        if exclude_duplicate_legs and 'DUPLICATE' in style: break
                        self.add_leg(leg_layer, xyz_start, xyz_end, style)
                        break
                    xyz_start = xyz_end

                if include_stations and fields[0] == 'NODE':
                    xyz = [float(v) for v in fields[1:4]]
                    name = fields[4].strip('[]')
                    flags = ' '.join(fields[5:])
                    if not station_layer:
                        station_layer = self.add_layer(title, 'stations', 'Point', epsg)
                        self.add_station_fields(station_layer)
                    while (True):
                        if exclude_surface_stations and 'SURFACE' in flags: break
                        self.add_station(station_layer, xyz, name, flags)
                        break
                

            if leg_layer:
                leg_layer.updateExtents() 
                QgsMapLayerRegistry.instance().addMapLayers([leg_layer])

            if station_layer:
                station_layer.updateExtents() 
                QgsMapLayerRegistry.instance().addMapLayers([station_layer])
