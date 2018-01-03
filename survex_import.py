# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SurvexImport
                                 A QGIS plugin
 Import survex .3d files
                              -------------------
        begin                : 2017-12-28
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Patrick B Warren
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

# from qgis.core import QgsMessageLog

from qgis.core import *
from PyQt4.QtCore import QVariant

from osgeo.osr import SpatialReference

from os import unlink as file_delete
from re import search as match_regex
from tempfile import NamedTemporaryFile
from subprocess import Popen, PIPE

leg_flags = ['DUPLICATE', 'SPLAY', 'SURFACE']
station_flags = ['SURFACE', 'EXPORTED', 'FIXED', 'ENTRANCE']

# Check newbie exception handling is correctly done

# Extract EPSG number from proj4 string from 3d file using GDAL tools.

def extract_epsg(proj4string):
    srs = SpatialReference()
    rc = srs.ImportFromProj4(proj4string)
    if rc: raise Exception("Invalid proj4 string: %s" % proj4string)
    code = srs.GetAttrValue('AUTHORITY', 1)
    return int(code)

def new_layer(title, subtitle, geom, epsg):
    uri = '%s?crs=epsg:%i' % (geom, epsg) if epsg else geom
    name = '%s %s' % (title, subtitle) if title else subtitle
    layer =  QgsVectorLayer(uri, name, 'memory')
    if not layer.isValid():
        raise Exception("Invalid layer with %s" % uri)
    return layer

def add_leg_fields(layer):
    pr = layer.dataProvider()
    attrs = [ QgsField(flag, QVariant.Int) for flag in leg_flags ]
    pr.addAttributes(attrs)
    layer.updateFields() 

def add_leg(layer, xyz_start, xyz_end, style):
    if layer is None: return
    pr = layer.dataProvider()
    xyz_pair = [QgsPointV2(QgsWKBTypes.PointZ, *xyz) for xyz in [xyz_start, xyz_end]]
    attrs = [1 if flag in style else 0 for flag in leg_flags ]
    linestring = QgsLineStringV2()
    linestring.setPoints(xyz_pair)
    feat = QgsFeature()
    geom = QgsGeometry(linestring)
    feat.setGeometry(geom) 
    feat.setAttributes(attrs)
    pr.addFeatures([feat])

def add_station_fields(layer):
    pr = layer.dataProvider()
    attrs = [QgsField(flag, QVariant.Int) for flag in station_flags]
    attrs.insert(0, QgsField('NAME', QVariant.String))
    pr.addAttributes(attrs)
    layer.updateFields() 

def add_station(layer, name, flags):
    if layer is None: return
    attrs = [1 if flag in flags else 0 for flag in station_flags ]
    attrs.insert(0, name)
    xyz = [float(v) for v in fields[1:4]]
    pr = layer.dataProvider()
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry(QgsPointV2(QgsWKBTypes.PointZ, *xyz)))
    feat.setAttributes(attrs)
    pr.addFeatures([feat])


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
        self.menu = self.tr(u'&Survex Import')
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
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/SurvexImport/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Import .3d files'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Survex Import'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def select_3d_file(self):
        filename = QFileDialog.getOpenFileName(self.dlg, "Select .3d file ","", '*.3d')
        self.dlg.selectedFile.setText(filename)

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.

            survex3dfile = self.dlg.selectedFile.text()

            include_legs = self.dlg.checkBoxLegs.isChecked()
            include_stations = self.dlg.checkBoxStations.isChecked()

            exclude_surface_legs = not self.dlg.checkBoxLegsSurface.isChecked()
            exclude_splay_legs = not self.dlg.checkBoxLegsSplay.isChecked()
            exclude_duplicate_legs = not self.dlg.checkBoxLegsDuplicate.isChecked()

            exclude_surface_stations = not self.dlg.checkBoxStationsSurface.isChecked()

            # catch all exceptions and deal with them at the end

            try:

                # Create a temporary file we can write dump3d output into

                f = NamedTemporaryFile(delete=False)
                f.close()

                dump3dfile = f.name

                if not os.path.exists(dump3dfile):
                    raise Exception("Couldn't create temporary file")

                # Run dump3d saving the output
                
                command = "dump3d %s > %s" % (survex3dfile, dump3dfile)
                p = Popen(command, shell=True, stderr=PIPE)
                rc = p.wait()
                err = p.stderr.read()

                if rc: raise Exception("dump3d failed with return code %i" % rc)

                # Now parse the dump3d output
    
                leg_layer, station_layer = None, None
                
                title, epsg = None, None

                legs = []

                # We run this like a gawk /pattern/ { action } script

                with open(dump3dfile) as fp:  
    
                    for line in iter(fp):

                        fields = line.split()
            
                        legs_append = False

                        if fields[0] == 'TITLE':
                            title = ' '.join(fields[1:]).strip('"')

                        if fields[0] == 'CS':
                            proj4string = ' '.join(fields[1:])
                            epsg = extract_epsg(proj4string)

                        if fields[0] == 'MOVE':
                            xyz_start = [float(v) for v in fields[1:4]]
        
                        if include_legs and fields[0] == 'LINE': 
                            xyz_end = [float(v) for v in fields[1:4]]
                            style = ' '.join(fields[5:])
                            if not leg_layer:
                                leg_layer = new_layer(title, 'legs', 'LineString', epsg)
                                add_leg_fields(leg_layer)
                            while (True):
                                if exclude_surface_legs and 'SURFACE' in style: break
                                if exclude_splay_legs and 'SPLAY' in style: break
                                if exclude_duplicate_legs and 'DUPLICATE' in style: break
                                add_leg(leg_layer, xyz_start, xyz_end, style)
                                break
                            xyz_start = xyz_end

                        if include_stations and fields[0] == 'NODE':
                            name = fields[4].strip('[]')
                            flags = ' '.join(fields[5:])
                            if not station_layer:
                                station_layer = new_layer(title, 'stations', 'Point', epsg)
                                add_station_fields(station_layer)
                            while (True):
                                if exclude_surface_stations and 'SURFACE' in flags: break
                                add_station(station_layer, name, flags)
                                break
                

                if leg_layer:
                    leg_layer.updateExtents() 
                    QgsMapLayerRegistry.instance().addMapLayers([leg_layer])

                if station_layer:
                    station_layer.updateExtents() 
                    QgsMapLayerRegistry.instance().addMapLayers([station_layer])

                file_delete(dump3dfile)

                # Here's where we catch all exceptions, cleaning up a possible
                # temporary file and re-raising the exception 

            except Exception as e:

                if dump3dfile and os.path.exists(dump3dfile):
                    file_delete(dump3dfile)

                raise

