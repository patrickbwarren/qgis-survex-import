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

File parser based on a library to handle Survex 3D files (*.3d) 
Copyright (C) 2008-2012 Thomas Holder, http://sf.net/users/speleo3/

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
from PyQt4.QtCore import QVariant, QDate

from osgeo.osr import SpatialReference

from struct import unpack
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

    # << perfection is achieved not when nothing more can be added 
    #      but when nothing more can be taken away >>

    # First try to match an explicit EPSG number, and check this is recognised.
    # If this fails, try to match the entire PROJ.4 string.  The reason for 
    # this somewhat convoluted route is to ensure if there is an EPSG number
    # in the passed argument, it is returned 'as is' and not transmuted
    # into another EPSG number with ostensibly the same CRS.

    def extract_epsg(self, proj4string):
        """Extract EPSG number from PROJ.4 string using GDAL tools"""
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

    # Note that 'PointZ' and 'LineStringZ' are not possible in QGIS 2.18
    # However the z-dimension data is respected.

    def add_layer(self, title, subtitle, geom, epsg):
        """Add a memory layer with title and geom 'Point' or 'LineString'"""
        uri = '%s?crs=epsg:%i' % (geom, epsg) if epsg else geom
        name = '%s - %s' % (title, subtitle) if title else subtitle
        layer =  QgsVectorLayer(uri, name, 'memory')
        if not layer.isValid():
            raise Exception("Invalid layer with %s" % uri)
        QgsMessageLog.logMessage("Memory layer '%s' called '%s' added" % (uri, name),
                                 tag='Import .3d', level=QgsMessageLog.INFO)
        return layer

    leg_attrs = {0x01 : 'SURFACE',
                 0x02 : 'DUPLICATE',
                 0x04 : 'SPLAY'}

    leg_flags = sorted(leg_attrs.keys())

    # Attributes are inserted like pushing onto a stack, so in reverse order
    
    def add_leg_fields(self, layer):
        """Add attributes (fields) for legs"""
        attrs = [QgsField(self.leg_attrs[k], QVariant.Int) for k in self.leg_flags]
        attrs.insert(0, QgsField('DATE2', QVariant.Date))
        attrs.insert(0, QgsField('DATE1', QVariant.Date))
        attrs.insert(0, QgsField('NAME', QVariant.String))
        layer.dataProvider().addAttributes(attrs)
        layer.updateFields() 
    
    def add_leg(self, layer, xyz_start, xyz_end, name, date_from, date_to, flag):
        """Add a leg into the legs layer, flag is raided for the attributes"""
        if not layer: return
        xyz_pair = [QgsPointV2(QgsWKBTypes.PointZ, *xyz) for xyz in [xyz_start, xyz_end]]
        attrs = [1 if flag & k else 0 for k in self.leg_flags]
        attrs.insert(0, date_to)
        attrs.insert(0, date_from)
        attrs.insert(0, name)
        linestring = QgsLineStringV2()
        linestring.setPoints(xyz_pair)
        feat = QgsFeature()
        geom = QgsGeometry(linestring)
        feat.setGeometry(geom) 
        feat.setAttributes(attrs)
        layer.dataProvider().addFeatures([feat])
        
    station_attrs = {0x01 : 'SURFACE',
                     0x02 : 'UNDERGROUND',
                     0x04 : 'ENTRANCE',
                     0x08 : 'EXPORTED',
                     0x10 : 'FIXED',
                     0x20 : 'ANON'}

    station_flags = sorted(station_attrs.keys())
    
    def add_station_fields(self, layer):
        """Add attributes (fields) for stations"""
        attrs = [QgsField(self.station_attrs[k], QVariant.Int) for k in self.station_flags]
        attrs.insert(0, QgsField('NAME', QVariant.String))
        layer.dataProvider().addAttributes(attrs)
        layer.updateFields() 

    def add_station(self, layer, xyz, name, flag):
        """Add a station into the stations layer, using flags as attributes"""
        if not layer: return
        attrs = [1 if flag & k else 0 for k in self.station_flags]
        attrs.insert(0, name)
        feat = QgsFeature()
        geom = QgsGeometry(QgsPointV2(QgsWKBTypes.PointZ, *xyz))
        feat.setGeometry(geom)
        feat.setAttributes(attrs)
        layer.dataProvider().addFeatures([feat])

    def read_xyz(self, fp):
        """Read xyz as signed integers according to .3d spec""" 
        return unpack('<iii', fp.read(12))
        
    def read_len(self, fp):
        """Read a number as a length according to .3d spec"""
        byte = ord(fp.read(1))
        if byte != 0xff:
            return byte
        else:
            return unpack('<I', fp.read(4))[0]

    def read_label(self, fp, current_label):
        """Read a string as a label, or part thereof, according to .3d spec"""
        byte = ord(fp.read(1))
        if byte != 0x00:
            ndel = byte >> 4
            nadd = byte & 0x0f
        else:
            ndel = self.read_len(fp)
            nadd = self.read_len(fp)
        oldlen = len(current_label)
        return current_label[:oldlen - ndel] + fp.read(nadd).decode('ascii')

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:

            # This is where all the work is done.

            survex3dfile = self.dlg.selectedFile.text()

            include_legs = self.dlg.checkLegs.isChecked()
            include_stations = self.dlg.checkStations.isChecked()

            exclude_surface_legs = not self.dlg.checkLegsSurface.isChecked()
            exclude_splay_legs = not self.dlg.checkLegsSplay.isChecked()
            exclude_duplicate_legs = not self.dlg.checkLegsDuplicate.isChecked()

            exclude_surface_stations = not self.dlg.checkStationsSurface.isChecked()

            get_crs = self.dlg.checkGetCRS.isChecked()

            title, epsg = None, None

            if not os.path.exists(survex3dfile):
                raise Exception("File '%s' doesn't exist" % survex3dfile)

            # Read .3d file as binary

            with open(survex3dfile, 'rb') as fp:
    
                line = fp.readline().rstrip() # File ID check
                
                if not line.startswith(b'Survex 3D Image File'):
                    raise IOError('Not a Survex 3D File: ' + survex3dfile)

                line = fp.readline().rstrip() # File format version
                
                if not line.startswith(b'v'):
                    raise IOError('Unrecognised .3d version: ' + survex3dfile)
                
                version = int(line[1:])
                if version < 8:
                    raise IOError('Version >= 8 required: ' + survex3dfile)

                line = fp.readline().rstrip() # Metadata (title and coordinate system)
                
                title, proj4string = [s.decode('utf-8') for s in line.split(b'\x00')]
                
                if get_crs:
                    epsg = self.extract_epsg(proj4string)

                line = fp.readline().rstrip() # Timestamp
                
                if not line.startswith(b'@'):
                    raise IOError('Unrecognised timestamp: ' + survex3dfile)
                
                timestamp = int(line[1:]) # Saved, but not used

                # System-wide flags

                flag = ord(fp.read(1))

                if flag & 0x80:
                    raise IOError('Flagged as extended elevation: ' + survex3dfile)

                # All front-end data read in, now read byte-wise
                # according to .3d spec.  Note that all elements must
                # be processed, in order, otherwise we get out of sync
    
                label = ''
                day_zero = QDate(1900, 1, 1)
                date1 = date2 = day_zero
                current_style = 0xff
                leg_layer, station_layer = None, None
            
                while True:

                    char = fp.read(1)

                    if not char: # End of file reached (prematurely?)
                        raise IOError('Premature end of file: ' + survex3dfile)

                    byte = ord(char)

                    if byte <= 0x05: # STYLE
                        if byte == 0x00 and current_style == 0x00: # this signals end of data
                            break # escape from byte-gobbling while loop
                        else:
                            current_style = byte
                
                    elif byte <= 0x0e: # Reserved
                        continue
        
                    elif byte == 0x0f: # MOVE
                        xyz = [0.01*v for v in self.read_xyz(fp)]

                    elif byte == 0x10: # DATE (none)
                        date1 = date2 = day_zero
                                    
                    elif byte == 0x11: # DATE (single date)
                        days = unpack('<H', fp.read(2))[0]
                        date1 = date2 = day_zero.addDays(days)
            
                    elif byte == 0x12:  # DATE (date range, short format)
                        days, extra = unpack('<HB', fp.read(3))
                        date1 = day_zero.addDays(days)
                        date2 = day_zero.addDays(days + extra + 1)

                    elif byte == 0x13: # DATE (date range, long format)
                        days1, days2 = unpack('<HH', fp.read(4)) 
                        date1 = day_zero.addDays(days1)
                        date2 = day_zero.addDays(days2)

                    elif byte <= 0x1e: # Reserved
                        continue
        
                    elif byte == 0x1f:  # Error info -- not currently captured
                        nlehv = unpack('<iiiii', fp.read(20))
            
                    elif byte <= 0x2f: # Reserved
                        continue
        
                    elif byte <= 0x31: # XSECT (short format) -- not currently captured
                        label = self.read_label(fp, label)
                        lrud = unpack('<hhhh', fp.read(8))
            
                    elif byte <= 0x33: # XSECT (long format) -- not currently captured
                        label = self.read_label(fp, label)
                        lrud = unpack('<iiii', fp.read(16))
            
                    elif byte <= 0x3f: # Reserved
                        continue
        
                    elif byte <= 0x7f: # LINE
                        flag = byte & 0x3f
                        if not (flag & 0x20):
                            label = self.read_label(fp, label)
                        xyz_prev = xyz
                        xyz = [0.01*v for v in self.read_xyz(fp)]
                        if include_legs:
                            if not leg_layer:
                                leg_layer = self.add_layer(title, 'legs', 'LineString', epsg)
                                self.add_leg_fields(leg_layer)
                            while (True):
                                if exclude_surface_legs and flag & 0x01: break
                                if exclude_duplicate_legs and flag & 0x02: break
                                if exclude_splay_legs and flag & 0x03: break
                                self.add_leg(leg_layer, xyz_prev, xyz, label, date1, date2, flag)
                                break

                    elif byte <= 0xff: # LABEL (or NODE)
                        flag = byte & 0x7f
                        label = self.read_label(fp, label)
                        xyz = [0.01*v for v in self.read_xyz(fp)]
                        if include_stations:
                            if not station_layer:
                                station_layer = self.add_layer(title, 'stations', 'Point', epsg)
                                self.add_station_fields(station_layer)
                            while (True):
                                if exclude_surface_stations and flag & 0x01 and not flag & 0x02: break
                                self.add_station(station_layer, xyz, label, flag)
                                break

                # End of byte-gobbling infinite while loop

            # file closes automatically, with open(survex3dfile, 'rb') as fp:
        
            if leg_layer:
                leg_layer.updateExtents() 
                QgsMapLayerRegistry.instance().addMapLayers([leg_layer])

            if station_layer:
                station_layer.updateExtents() 
                QgsMapLayerRegistry.instance().addMapLayers([station_layer])
