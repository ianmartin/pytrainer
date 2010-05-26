# -*- coding: iso-8859-1 -*-

#Copyright (C) Fiz Vazquez vud1@sindominio.net

#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; either version 2
#of the License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

import logging
import os
from lxml import etree
import dateutil.parser
from dateutil.tz import * # for tzutc()

from pytrainer.lib.gpx import Gpx
from pytrainer.lib.unitsconversor import *

class Activity:
	'''
	Class that knows everything about a particular activity

	tracks			- (list) tracklist from gpx
	tracklist		- (list of dict) trackpoint data from gpx
	laps			- (list of dict) lap list
	tree			- (ElementTree) parsed xml of gpx file
	us_system		- (bool) True: imperial measurement False: metric measurement
	distance_unit	- (string) unit to use for distance
	speed_unit		- (string) unit to use for speed
	height_unit		- (string) unit to use for height
	gpx_file		- (string) gpx file name
	gpx				- (Gpx class) actual gpx instance
	sport_name		- (string) sport name
	sport_id		- (string) id for sport in sports table
	title			- (string) title of activity
	date			- (string) date of activity
	time			- (int) activity duration in seconds
	beats			- (int) average heartrate for activity
	maxbeats 		- (int) maximum heartrate for activity
	comments		- (string) activity comments
	calories		- (int) calories of activity
	id_record		- (string) id for activity in records table
	date_time_local	- (string) date and time of activity in local timezone
	date_time_utc	- (string) date and time of activity in UTC timezone
	date_time		- (datetime) date and time of activity in local timezone
	distance 		- (float) activity distance
	average			- (float) average speed of activity
	upositive 		- (float) height climbed during activity
	unegative		- (float) height decended during activity
	maxspeed 		- (float) maximum speed obtained during activity
	maxpace 		- (float) maxium pace obtained during activity
	pace			- (float) average pace for activity
	has_data		- (bool) true if gpx processed and instance has data populated
	'''
	def __init__(self, pytrainer_main = None, id = None):
		logging.debug(">>")
		self.id = id
		#It is an error to try to initialise with no id
		if self.id is None:
			return
		#It is an error to try to initialise with no reference to pytrainer_main
		if pytrainer_main is None:
			print("Error - must initialise with a reference to the main pytrainer class")
			return
		self.pytrainer_main = pytrainer_main
		self.tracks = None
		self.laps = None
		self.tree = None
		self.has_data = False
		if self.pytrainer_main.profile.getValue("pytraining","prf_us_system") == "True":
			self.us_system = True
		else:
			self.us_system = False
		self._set_units()
		self.gpx_file = "%s/%s.gpx" % (self.pytrainer_main.profile.gpxdir, id)
		#It is OK to not have a GPX file for an activity - this just limits us to information in the DB
		if not os.path.isfile(self.gpx_file):
			self.gpx_file = None
			logging.debug("No GPX file found for record id: %s" % id)
		if self.gpx_file is not None:
			self._init_from_gpx_file()
		self._init_from_db()
		logging.debug("<<")

	def _set_units(self):
		if self.us_system:
			self.distance_unit = _("miles")
			self.speed_unit = _("miles/h")
			self.pace_unit = _("min/mile")
			self.height_unit = _("feet")
		else:
			self.distance_unit = _("km")
			self.speed_unit = _("km/h")
			self.pace_unit = _("min/km")
			self.height_unit = _("m")

	def _init_from_gpx_file(self):
		'''
		Get activity information from the GPX file
		'''
		logging.debug(">>")
		#Parse GPX file
		print "Activity initing GPX.. ",
		self.gpx = Gpx(filename = self.gpx_file) #TODO change GPX code to do less....
		self.tree = self.gpx.tree
		self.tracks = self.gpx.getTrackList() #TODO fix - this should removed and replaced with self.tracklist functionality
		self.tracklist = self.gpx.trkpoints
		logging.debug("<<")

	def _init_from_db(self):
		'''
		Get activity information from the DB
		'''
		logging.debug(">>")
		#Get base information
		db_result = self.pytrainer_main.ddbb.select_dict("records,sports",
					("sports.name","id_sports", "date","distance","time","beats","comments",
						"average","calories","id_record","title","upositive","unegative",
						"maxspeed","maxpace","pace","maxbeats","date_time_utc","date_time_local"),
					"id_record=\"%s\" and records.sport=sports.id_sports" %self.id)
		if len(db_result) == 1:
			dict = db_result[0]
			self.sport_name = dict['sports.name']
			self.sport_id = dict['id_sports']
			self.title = dict['title']
			self.date = dict['date']
			self.time = self._int(dict['time'])
			self.beats = self._int(dict['beats'])
			self.comments = dict['comments']
			self.calories = self._int(dict['calories'])
			self.id_record = dict['id_record']
			self.maxbeats = self._int(dict['maxbeats'])
			#Sort time....
			# ... use local time if available otherwise use date_time_utc and create a local datetime...
			self.date_time_local = dict['date_time_local']
			self.date_time_utc = dict['date_time_utc']
			if self.date_time_local is not None: #Have a local time stored in DB
				self.date_time = dateutil.parser.parse(self.date_time_local)
			else: #No local time in DB
				tmpDateTime = dateutil.parser.parse(self.date_time_utc)
				self.date_time = tmpDateTime.astimezone(tzlocal()) #datetime with localtime offset (using value from OS)
			#Sort data that changes for the US etc
			if self.us_system:
				self.distance = km2miles(self._float(dict['distance']))
				self.average = km2miles(self._float(dict['average']))
				self.upositive = m2feet(self._float(dict['upositive']))
				self.unegative = m2feet(self._float(dict['unegative']))
				self.maxspeed = km2miles(self._float(dict['maxspeed']))
				self.maxpace = pacekm2miles(self._float(dict['maxpace']))
				self.pace = pacekm2miles(self._float(dict['pace']))
			else:
				self.distance = self._float(dict['distance'])
				self.average = self._float(dict['average'])
				self.upositive = self._float(dict['upositive'])
				self.unegative = self._float(dict['unegative'])
				self.maxspeed = self._float(dict['maxspeed'])
				self.maxpace = self._float(dict['maxpace'])
				self.pace = self._float(dict['pace'])
			self.has_data = True
		else:
			raise Exception( "Error - multiple results from DB for id: %s" % self.id )
		#Get lap information
		laps = self.pytrainer_main.ddbb.select_dict("laps",
					("id_lap", "record", "elapsed_time", "distance", "start_lat", "start_lon", "end_lat", "end_lon", "calories", "lap_number"),
					"record=\"%s\"" % self.id)
		if laps is None or laps == [] or len(laps) < 1:  #No laps found
			logging.debug("No laps in DB for record %d" % self.id)
			if self.gpx_file is not None:
				laps = self._get_laps_from_gpx()
		self.laps = laps
		logging.debug("<<")

	def _get_laps_from_gpx(self):
		logging.debug(">>")
		laps = []
		gpxLaps = self.gpx.getLaps()
		for lap in gpxLaps:
			lap_number = gpxLaps.index(lap)
			tmp_lap = {}
			tmp_lap['record'] = self.id
			tmp_lap['lap_number'] = lap_number
			tmp_lap['elapsed_time'] = lap[0]
			tmp_lap['distance'] = lap[4]
			tmp_lap['start_lat'] = lap[5]
			tmp_lap['start_lon'] = lap[6]
			tmp_lap['end_lat'] = lap[1]
			tmp_lap['end_lon'] = lap[2]
			tmp_lap['calories'] = lap[3]
			laps.append(tmp_lap)
		if laps is not None:
			for lap in laps:
				lap_keys = ", ".join(map(str, lap.keys()))
				lap_values = lap.values()
				self.pytrainer_main.record.insertLaps(lap_keys,lap.values())
		logging.debug("<<")
		return laps

	def _float(self, value):
		try:
			result = float(value)
		except:
			result = 0.0
		return result

	def _int(self, value):
		try:
			result = int(value)
		except:
			result = 0
		return result