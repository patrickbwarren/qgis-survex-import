#!/usr/bin/env python
"""
import3d.py
Python script for importing reduced survey data (.3d file) into QGIS.
It can be added as a user script to the Processing Toolbox. 

Copyright (C) 2017 Patrick B Warren

Email: patrickbwarren@gmail.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see
<http://www.gnu.org/licenses/>.
"""

# change the following as desired

survex3dfile = "/home/patrick/GitHub/qgis-survex-import/DowProv/DowProv.3d"

include_legs = True
include_stations = True

from qgis.core import *
from PyQt4.QtCore import QVariant

from osgeo.osr import SpatialReference

from os import unlink as file_delete
from os.path import exists as file_exists
from re import search as match_regex
from tempfile import NamedTemporaryFile
from subprocess import Popen, PIPE

leg_flags = ['DUPLICATE', 'SPLAY', 'SURFACE']
station_flags = ['SURFACE', 'EXPORTED', 'FIXED', 'ENTRANCE']

# Check newbie exception handling is correctly done

# Extract EPSG number from proj4 string from 3d file
# should check EPSG code is recognised by QGIS
# Add code in here to attempt to match proj4 string if no EPSG

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
                    
def add_station(layer, fields):
    if layer is None: return
    name = fields[4].strip('[]')
    flags = ' '.join(fields[5:])
    attrs = [1 if flag in flags else 0 for flag in station_flags ]
    attrs.insert(0, name)
    xyz = [float(v) for v in fields[1:4]]
    pr = layer.dataProvider()
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry(QgsPointV2(QgsWKBTypes.PointZ, *xyz)))
    feat.setAttributes(attrs)
    pr.addFeatures([feat])

# Construct a named temporary file that we can redirect dump3d output
# to.  This file is deleted at the end.  We catch all exceptions to
# make sure this happens (re-raise exception at end)

# In order to get a return code from the process, we use
# subprocess.Popen which is in Python 2.4 onwards (released 2004).

dump3dfile = None

try:

    f = NamedTemporaryFile(delete=False)
    f.close()
    dump3dfile = f.name

    if not file_exists(dump3dfile):
        raise Exception("Couldn't create temporary file")

    command = "dump3d %s > %s" % (survex3dfile, dump3dfile)
    p = Popen(command, shell=True, stderr=PIPE)
    rc = p.wait()
    err = p.stderr.read()

    if rc: raise Exception("dump3d failed with return code %i" % rc)

    # If we got this far then we have the dump3d output in a temporary file
    
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
                add_leg(leg_layer, xyz_start, xyz_end, style)
                xyz_start = xyz_end

            if include_stations and fields[0] == 'NODE':
                if not station_layer:
                    station_layer = new_layer(title, 'stations', 'Point', epsg)
                    add_station_fields(station_layer)
                add_station(station_layer, fields)
                

    if leg_layer:
        leg_layer.updateExtents() 
        QgsMapLayerRegistry.instance().addMapLayers([leg_layer])

    if station_layer:
        station_layer.updateExtents() 
        QgsMapLayerRegistry.instance().addMapLayers([station_layer])

    file_delete(dump3dfile)

# Here's where we catch all exceptions, cleaning up a possible
# temporary file and re-raising a custom exception

except Exception as e:

    if dump3dfile and file_exists(dump3dfile):
        file_delete(dump3dfile)

    raise GeoAlgorithmExecutionException(str(e))
