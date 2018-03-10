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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFileInfo
from PyQt4.QtGui import QAction, QIcon, QFileDialog
from qgis.gui import QgsMessageBar
from qgis.core import *
from PyQt4.QtCore import QVariant, QDate
from qgis.core import QgsVectorFileWriter
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from survex_import_dialog import SurvexImportDialog

import os.path

from osgeo.osr import SpatialReference
from struct import unpack
from re import sub, search
from math import sqrt # needed for LRUD wall calculations

class SurvexImport:
    """QGIS Plugin Implementation."""

    type_convert = {QGis.WKBPoint: QgsWKBTypes.PointZ,
                    QGis.WKBLineString: QgsWKBTypes.LineStringZ,
                    QGis.WKBMultiPolygon: QgsWKBTypes.MultiPolygonZ}

    style_type = {0x00:'NORMAL', 0x01:'DIVING', 0x02:'CARTESIAN',
                  0x03:'CYLPOLAR', 0x04:'NOSURVEY', 0xff:'NOSTYLE'}

    leg_attr = {0x01:'SURFACE', 0x02:'DUPLICATE', 0x04:'SPLAY'}
    leg_flags = sorted(leg_attr.keys())
    
    station_attr = {0x01:'SURFACE', 0x02:'UNDERGROUND', 0x04:'ENTRANCE',
                    0x08:'EXPORTED', 0x10:'FIXED', 0x20:'ANON'}
    station_flags = sorted(station_attr.keys())
            
    leg_list = []
    station_list = []
    station_xyz = {}
    xsect_list = []
    title = ''

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
        
        self.dlg.selectedDir.clear()
        self.dlg.dirSelector.clicked.connect(self.select_dir)

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
        filename = QFileDialog.getOpenFileName(self.dlg, "Select .3d file ", "",  '*.3d')
        self.dlg.selectedFile.setText(filename)

        # to be done - remember last-used path
        # QString fileName = QFileDialog::getOpenFileName(this, caption, path);
        # if (!fileName.isNull()) {
        #    ...
        #    path = QFileInfo(fileName).path(); // store path for next time
        # }

    def select_dir(self):
        savedir = QFileDialog.getExistingDirectory(self.dlg, "Select directory for ESRI shapefiles", "")
        self.dlg.selectedDir.setText(savedir)

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
            raise Exception("Invalid proj4 string: " + proj4string)
        code = srs.GetAttrValue('AUTHORITY', 1)
        epsg = int(code)
        msg = "PROJ.4 %s --> EPSG:%i" % (proj4string, epsg)
        QgsMessageLog.logMessage(msg, tag='Import .3d', level=QgsMessageLog.INFO)
        return epsg

    # Note that 'PointZ', 'LineStringZ', 'PolygonZ' are not possible
    # in QGIS 2.18 However the z-dimension data is respected.

    def add_layer(self, subtitle, geom, epsg):
        """Add a memory layer with title and geom 'Point' or 'LineString'"""
        uri = '%s?crs=epsg:%i' % (geom, epsg) if epsg else geom
        name = '%s - %s' % (self.title, subtitle) if self.title else subtitle
        layer =  QgsVectorLayer(uri, name, 'memory')
        if not layer.isValid():
            raise Exception("Invalid layer with %s" % uri)
        msg = "Memory layer '%s' called '%s' added" % (uri, name)
        QgsMessageLog.logMessage(msg, tag='Import .3d', level=QgsMessageLog.INFO)
        return layer

    def read_xyz(self, fp):
        """Read xyz as integers, according to .3d spec""" 
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
            include_polygons = self.dlg.checkPolygons.isChecked()
            include_walls = self.dlg.checkWalls.isChecked()
            include_xsections = self.dlg.checkXSections.isChecked()
            include_traverses = self.dlg.checkTraverses.isChecked()

            exclude_surface_legs = not self.dlg.checkLegsSurface.isChecked()
            exclude_splay_legs = not self.dlg.checkLegsSplay.isChecked()
            exclude_duplicate_legs = not self.dlg.checkLegsDuplicate.isChecked()
            exclude_surface_stations = not self.dlg.checkStationsSurface.isChecked()

            use_clino_wgt = self.dlg.checkClinoWeights.isChecked()

            discard_features = not self.dlg.checkKeepFeatures.isChecked()
            
            get_crs = self.dlg.checkGetCRS.isChecked()

            if not os.path.exists(survex3dfile):
                raise Exception("File '%s' doesn't exist" % survex3dfile)

            if discard_features:
                self.leg_list = []
                self.station_list = []
                self.station_xyz = {}
                self.xsect_list = []

            # Read .3d file as binary, parse and save data structures
            
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
                fields = line.split(b'\x00')
                
                previous_title = '' if discard_features else self.title
                if previous_title:
                    self.title = previous_title + ' + ' + fields[0];
                else:
                    self.title = fields[0];

                # Try to work out EPSG number from CS if available and asked-for
                
                epsg = self.extract_epsg(fields[1]) if get_crs and len(fields) > 1 else None

                line = fp.readline().rstrip() # Timestamp (not used)
                
                if not line.startswith(b'@'):
                    raise IOError('Unrecognised timestamp: ' + survex3dfile)
                
                timestamp = int(line[1:]) # Saved, but not used at present

                # System-wide flags - abort if extended elevation

                flag = ord(fp.read(1))

                if flag & 0x80:
                    raise IOError('Extended elevation: ' + survex3dfile)

                # All front-end data read in, now read byte-wise
                # according to .3d spec.  Note that all elements must
                # be processed, in order, otherwise we get out of sync
    
                date0 = date1 = date2 = QDate(1900, 1, 1)

                label, style = '', 0xff
                
                legs = [] # will be used to capture leg data between MOVEs
                xsect = [] # will be used to capture XSECT data
                nlehv = None # In case there isn't any
                    
                while True:

                    char = fp.read(1)

                    if not char: # End of file reached (prematurely?)
                        raise IOError('Premature end of file: ' + survex3dfile)

                    byte = ord(char)

                    if byte <= 0x05: # STYLE
                        if byte == 0x00 and style == 0x00: # this signals end of data
                            if legs: # there may be a pending list of legs to save
                                self.leg_list.append((legs,  nlehv))
                            break # escape from byte-gobbling while loop
                        else:
                            style = byte
                
                    elif byte <= 0x0e: # Reserved
                        continue
        
                    elif byte == 0x0f: # MOVE
                        xyz = self.read_xyz(fp)
                        if legs:
                            self.leg_list.append((legs,  nlehv))
                            legs = []

                    elif byte == 0x10: # DATE (none)
                        date1 = date2 = date0
                                    
                    elif byte == 0x11: # DATE (single date)
                        days = unpack('<H', fp.read(2))[0]
                        date1 = date2 = date0.addDays(days)
            
                    elif byte == 0x12:  # DATE (date range, short format)
                        days, extra = unpack('<HB', fp.read(3))
                        date1 = date0.addDays(days)
                        date2 = date0.addDays(days + extra + 1)

                    elif byte == 0x13: # DATE (date range, long format)
                        days1, days2 = unpack('<HH', fp.read(4)) 
                        date1 = date0.addDays(days1)
                        date2 = date0.addDays(days2)

                    elif byte <= 0x1e: # Reserved
                        continue
        
                    elif byte == 0x1f:  # Error info
                        nlehv = unpack('<iiiii', fp.read(20))
            
                    elif byte <= 0x2f: # Reserved
                        continue
            
                    elif byte <= 0x33: # XSECT
                        label = self.read_label(fp, label)
                        if byte & 0x02:
                            lrud = unpack('<iiii', fp.read(16))
                        else:
                            lrud = unpack('<hhhh', fp.read(8))
                        xsect.append((label, lrud))
                        if byte & 0x01: # XSECT_END
                            self.xsect_list.append(xsect)
                            xsect = []
            
                    elif byte <= 0x3f: # Reserved
                        continue
        
                    elif byte <= 0x7f: # LINE
                        flag = byte & 0x3f
                        if not (flag & 0x20):
                            label = self.read_label(fp, label)
                        xyz_prev = xyz
                        xyz = self.read_xyz(fp)
                        while (True):
                            if exclude_surface_legs and flag & 0x01: break
                            if exclude_duplicate_legs and flag & 0x02: break
                            if exclude_splay_legs and flag & 0x04: break
                            legs.append(((xyz_prev, xyz), label, style, date1, date2, flag))
                            break

                    elif byte <= 0xff: # LABEL (or NODE)
                        flag = byte & 0x7f
                        label = self.read_label(fp, label)
                        xyz = self.read_xyz(fp)
                        while (True):
                            if exclude_surface_stations and flag & 0x01 and not flag & 0x02: break
                            self.station_list.append((xyz, label, flag))
                            break
                        self.station_xyz[label] = xyz

                # End of byte-gobbling while loop

            # file closes automatically, with open(survex3dfile, 'rb') as fp:

            # Now create the layers in QGIS.  Attributes are inserted
            # like pushing onto a stack, so in reverse order.  Layers
            # are created only if required and data is available.
            # If nlehv is not None, then error data has been provided.

            
            layers = [] # used to keep a list of the created layers

            if include_legs and self.leg_list:
                
                leg_layer = self.add_layer('legs', 'LineString', epsg)
                
                attrs = [QgsField(self.leg_attr[k], QVariant.Int) for k in self.leg_flags]
                if nlehv:
                    [ attrs.insert(0, QgsField(s, QVariant.Double)) for s in ('ERROR_VERT', 'ERROR_HORIZ', 'ERROR', 'LENGTH')]
                    attrs.insert(0, QgsField('NLEGS', QVariant.Int))
                attrs.insert(0, QgsField('DATE2', QVariant.Date))
                attrs.insert(0, QgsField('DATE1', QVariant.Date))
                attrs.insert(0, QgsField('STYLE', QVariant.String))
                attrs.insert(0, QgsField('ELEVATION', QVariant.Double))
                attrs.insert(0, QgsField('NAME', QVariant.String))
                leg_layer.dataProvider().addAttributes(attrs)
                leg_layer.updateFields()
                
                features = []

                for legs, nlehv in self.leg_list:
                    for (xyz_pair, label, style, from_date, to_date, flag) in legs:
                        elev = 0.5 * sum([0.01*xyz[2] for xyz in xyz_pair])
                        points = []
                        for xyz in xyz_pair:
                            x, y, z = [0.01*v for v in xyz]
                            points.append(QgsPointV2(QgsWKBTypes.PointZ, x, y, z))
                        attrs = [1 if flag & k else 0 for k in self.leg_flags]
                        if nlehv:
                            [ attrs.insert(0, 0.01*v) for v in reversed(nlehv[1:5]) ]
                            attrs.insert(0, nlehv[0])
                        attrs.insert(0, to_date)
                        attrs.insert(0, from_date)
                        attrs.insert(0, self.style_type[style])
                        attrs.insert(0, round(elev, 2))
                        attrs.insert(0, label)
                        linestring = QgsLineStringV2()
                        linestring.setPoints(points)
                        feat = QgsFeature()
                        geom = QgsGeometry(linestring)
                        feat.setGeometry(geom) 
                        feat.setAttributes(attrs)
                        features.append(feat)
                    
                leg_layer.dataProvider().addFeatures(features)
                layers.append(leg_layer)

            if include_stations and self.station_list:
                
                station_layer = self.add_layer('stations', 'Point', epsg)
    
                attrs = [QgsField(self.station_attr[k], QVariant.Int) for k in self.station_flags]
                attrs.insert(0, QgsField('ELEVATION', QVariant.Double))
                attrs.insert(0, QgsField('NAME', QVariant.String))
                station_layer.dataProvider().addAttributes(attrs)
                station_layer.updateFields() 
    
                features = []

                for (xyz, label, flag) in self.station_list:
                    x, y, z = [0.01*v for v in xyz]
                    attrs = [1 if flag & k else 0 for k in self.station_flags]
                    attrs.insert(0, round(z, 2))
                    attrs.insert(0, label)
                    feat = QgsFeature()
                    geom = QgsGeometry(QgsPointV2(QgsWKBTypes.PointZ, x, y, z))
                    feat.setGeometry(geom)
                    feat.setAttributes(attrs)
                    features.append(feat)
                    
                station_layer.dataProvider().addFeatures(features)
                layers.append(station_layer)

            # The calculations below use integers for xyz and
            # conversion to metres is left to the end.  Then dh2 is an
            # integer and the test for a plumb is safely dh2 = 0.
            
            if (include_polygons or include_walls) and self.xsect_list:
                                
                trav_features = []
                wall_features = []
                xsect_features = []
                quad_features = []
                
                for xsect in self.xsect_list:

                    if len(xsect) < 2: # bail out if there's only one station
                        continue

                    centerline = [] # will contain the station position and LR data

                    for label, lrud in xsect:
                        xyz = self.station_xyz[label] # look up coordinates from label
                        lr = tuple([max(0, v) for v in lrud[0:2]]) # clear missing LR data
                        centerline.append(xyz + lr) # and collect as 5-uple

                    direction = [] # will contain the corresponding direction vectors

                    # The directions are unit vectors optionally
                    # weighted by cos(inclination) = dh/dl where
                    # dh^2 = dx^2 + dy^2 + dz^2 and dl^2 = dh^2 +
                    # dz^2.  The normalisation is correspondingly
                    # either 1/dh, or 1/dh * dh/dl = 1/dl.

                    for i, (x, y, z, l, r) in enumerate(centerline):
                        if i > 0:
                            dx, dy, dz = x - xp, y - yp, z - zp
                            dh2 = dx*dx + dy*dy # integer horizontal displacement (mm^2)
                            norm = sqrt(dh2 + dz*dz) if use_clino_wgt else sqrt(dh2)
                            dx, dy = (dx/norm, dy/norm) if dh2 > 0 and norm > 0 else (0, 0)
                            direction.append((dx, dy))
                        xp, yp, zp = x, y, z

                    left_wall = []
                    right_wall = []

                    # We build the walls by walking through the list
                    # of stations and directions, with simple defaults
                    # for the start and end stations
                    
                    for i, (x, y, z, l, r) in enumerate(centerline):
                        d1x, d1y = direction[i-1] if i > 0 else (0, 0)
                        d2x, d2y = direction[i] if i+1 < len(centerline) else (0, 0)
                        dx, dy = d1x+d2x, d1y+d2y # mean (sum of) direction vectors
                        norm = sqrt(dx*dx + dy*dy) # normalise to unit vector
                        ex, ey = (dx/norm, dy/norm) if norm > 0 else (0, 0)
                        # Convert to metres when saving the points
                        left_wall.append((0.01*(x-l*ey), 0.01*(y+l*ex), 0.01*z))
                        right_wall.append((0.01*(x+r*ey), 0.01*(y-r*ex), 0.01*z))

                    # Mean elevation of centerline, used for elevation attribute
                    
                    elev = 0.01 * sum([xyzlr[2] for xyzlr in centerline]) / len(centerline)
                    attrs = [round(elev, 2)]

                    # Now create the feature sets - first the centerline traverse

                    points = []

                    for xyzlr in centerline:
                        xyz = [0.01*v for v in xyzlr[0:3]] # These were mm, convert to metres
                        points.append(QgsPointV2(QgsWKBTypes.PointZ, *xyz))
                        
                    linestring = QgsLineStringV2()
                    linestring.setPoints(points)
                    feat = QgsFeature()
                    geom = QgsGeometry(linestring)
                    feat.setGeometry(geom)
                    feat.setAttributes(attrs)
                    trav_features.append(feat)

                    # The walls as line strings

                    for wall in (left_wall, right_wall):
                        
                        points = [QgsPointV2(QgsWKBTypes.PointZ, *xyz) for xyz in wall]
                        linestring = QgsLineStringV2()
                        linestring.setPoints(points)
                        feat = QgsFeature()
                        geom = QgsGeometry(linestring)
                        feat.setGeometry(geom) 
                        feat.setAttributes(attrs)
                        wall_features.append(feat)

                    # Slightly more elaborate, pair up points on left
                    # and right walls, and build a cross section as a
                    # 2-point line string, and a quadrilateral polygon
                    # (a closed 5-point line string for the exterior
                    # ring of the polygon).  Note that polygons in
                    # QGIS are supposed to have their points ordered
                    # clockwise.

                    for i, xyz_pair in enumerate(zip(left_wall, right_wall)):

                        elev = 0.01 * centerline[i][2] # elevation of station in centerline
                        attrs = [round(elev, 2)]
                        points = [QgsPointV2(QgsWKBTypes.PointZ, *xyz) for xyz in xyz_pair]
                        linestring = QgsLineStringV2()
                        linestring.setPoints(points)
                        feat = QgsFeature()
                        geom = QgsGeometry(linestring)
                        feat.setGeometry(geom) 
                        feat.setAttributes(attrs)
                        xsect_features.append(feat)

                        if i > 0:
                            elev = 0.5*(prev_xyz_pair[0][2] + xyz_pair[0][2]) # average elevation
                            attrs = [round(elev, 2)]
                            points = []
                            for xyz in tuple(reversed(prev_xyz_pair)) + xyz_pair + (prev_xyz_pair[1],):
                                points.append(QgsPointV2(QgsWKBTypes.PointZ, *xyz))
                            linestring = QgsLineStringV2()
                            linestring.setPoints(points)
                            polygon = QgsPolygonV2()
                            polygon.setExteriorRing(linestring)
                            feat = QgsFeature()
                            geom = QgsGeometry(polygon)
                            feat.setGeometry(geom)
                            feat.setAttributes(attrs)
                            quad_features.append(feat)
                            
                        prev_xyz_pair = xyz_pair

                # End of processing xsect_list - now add features to requested layers

                attrs = [QgsField('ELEVATION', QVariant.Double)] # common to all

                if include_polygons and quad_features:
                    quads_layer = self.add_layer('polygons', 'MultiPolygon', epsg)
                    quads_layer.dataProvider().addAttributes(attrs)
                    quads_layer.updateFields()
                    quads_layer.dataProvider().addFeatures(quad_features)
                    layers.append(quads_layer)
                    
                if include_walls and wall_features:
                    walls_layer = self.add_layer('walls', 'LineString', epsg)
                    walls_layer.dataProvider().addAttributes(attrs)
                    walls_layer.updateFields()
                    walls_layer.dataProvider().addFeatures(wall_features)
                    layers.append(walls_layer)

                if include_xsections and xsect_features:
                    xsects_layer = self.add_layer('xsections', 'LineString', epsg)
                    xsects_layer.dataProvider().addAttributes(attrs)
                    xsects_layer.updateFields()
                    xsects_layer.dataProvider().addFeatures(xsect_features)
                    layers.append(xsects_layer)

                if include_traverses and trav_features:
                    travs_layer = self.add_layer('traverses', 'LineString', epsg)
                    travs_layer.dataProvider().addAttributes(attrs)
                    travs_layer.updateFields()
                    travs_layer.dataProvider().addFeatures(trav_features)
                    layers.append(travs_layer)

            # End of adding polygons and/or walls - now add all created layers

            if layers:
                [ layer.updateExtents() for layer in layers ]
                QgsMapLayerRegistry.instance().addMapLayers(layers)

            # Save layers to shapefiles if directory has been selected
            # create directory if necessary

            if self.dlg.selectedDir.text():
                output_dir = self.dlg.selectedDir.text() + '/'
                # create directory if it doesn't exist
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                for layer in layers:
                    shape_file = layer.name()
                    shape_file = sub(' - ', '_', shape_file) # replace ' - ' in layer name with underscore
                    shape_file = sub(' + ', '_', shape_file) # ditto for ' + ' for multiple imports
                    shape_file = sub(r"[^\w\s]", '', shape_file) # remove remaining non-word characters except numbers and letters
                    layer_type = layer.wkbType()
                    if layer_type in self.type_convert:
                        override_type = self.type_convert[layer_type]
                    else:
                        override_type = QgsWKBTypes.Unknown
                    msg = "DEBUGGING: shapefile=%s wkbType=%i QgsWKBType=%i" % (shape_file, layer_type, override_type)
                    QgsMessageLog.logMessage(msg, tag='Import .3d', level=QgsMessageLog.INFO)
                    writer = QgsVectorFileWriter.writeAsVectorFormat(layer, output_dir + shape_file, "utf-8", layer.crs(), "ESRI Shapefile",
                                                                     overrideGeometryType=override_type, includeZ=True)
                    if writer == QgsVectorFileWriter.NoError:
                        self.iface.messageBar().pushMessage("Layer Saved", layer.name()+' saved to '+shape_file+' in '+output_dir,
                                                            level=QgsMessageBar.INFO, duration=3)
                    else:
                        self.iface.messageBar().pushMessage("Error saving layer:", layer.name()+' to '+shape_file+' in '+output_dir,
                                                            level=QgsMessageBar.CRITICAL, duration=3)

        # End of if results in run function

    # End of run function definition

# That's it
