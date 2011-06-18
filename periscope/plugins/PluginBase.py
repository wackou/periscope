# -*- coding: utf-8 -*-

#   This file is part of periscope.
#
#    periscope is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import abc
import logging
import os
import re
import sys
import urllib2
import struct
import threading
import gzip, zipfile
import cStringIO as StringIO

class PluginBase(object):
	__metaclass__ = abc.ABCMeta
	multi_languages_queries = False
	multi_filename_queries = False
	api_based = True
	timeout = 3
	user_agent = 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3)'
	lock = threading.Lock()

	@abc.abstractmethod
	def __init__(self, pluginLanguages, config_dict=None, isRevert=False):
		self.config_dict = config_dict
		if not pluginLanguages:
			self.pluginLanguages = None
			self.revertPluginLanguages = None
		elif not isRevert:
			self.pluginLanguages = pluginLanguages
			self.revertPluginLanguages = dict((v, k) for k, v in self.pluginLanguages.iteritems())
		else:
			self.revertPluginLanguages = pluginLanguages
			self.pluginLanguages = dict((v, k) for k, v in self.revertPluginLanguages.iteritems())
		self.logger = logging.getLogger('periscope.%s' % self.getClassName())

	@staticmethod
	def getFileName(filepath):
		filename = filepath
		if os.path.isfile(filename):
			filename = os.path.basename(filename)
		if filename.endswith(('.avi', '.wmv', '.mov', '.mp4', '.mpeg', '.mpg', '.mkv')):
			filename = filename.rsplit('.', 1)[0]
		return filename

	def hashFile(self, filename):
		''' Calculates the Hash à-la Media Player Classic as it is the hash used by OpenSubtitles.
		By the way, this is not a very robust hash code. '''
		longlongformat = 'q'  # long long
		bytesize = struct.calcsize(longlongformat)
		f = open(filename, "rb")
		filesize = os.path.getsize(filename)
		hash = filesize
		if filesize < 65536 * 2:
			self.logger.error("File %s is too small (SizeError < 2**16)" % filename)
			return []
		for x in range(65536 / bytesize):
			buffer = f.read(bytesize)
			(l_value,) = struct.unpack(longlongformat, buffer)
			hash += l_value
			hash = hash & 0xFFFFFFFFFFFFFFFF #to remain as 64bit number
		f.seek(max(0, filesize - 65536), 0)
		for x in range(65536 / bytesize):
			buffer = f.read(bytesize)
			(l_value,) = struct.unpack(longlongformat, buffer)
			hash += l_value
			hash = hash & 0xFFFFFFFFFFFFFFFF
		f.close()
		returnedhash = "%016x" % hash
		return returnedhash

	def downloadFile(self, url, filename, data=None):
		''' Downloads the given url to the given filename '''
                open(filename, 'wb').write(self._downloadText(url, data))
                self.logger.debug("Download finished for file %s. Size: %s" % (filename, os.path.getsize(filename)))


        def _downloadText(self, url, data = None):
                ''' Downloads the given url and return it as a string '''
                self.logger.info("Downloading %s" % url)
                try:
                        req = urllib2.Request(url, headers={'Referer': url, 'User-Agent': self.user_agent})
                        f = urllib2.urlopen(req, data=data)
                        result = f.read()
                        f.close()
                        return result
                except urllib2.HTTPError, e:
                        self.logger.error("HTTP Error:", e.code , url)
                except urllib2.URLError, e:
                        self.logger.error("URL Error:", e.reason , url)

                return ''


        def downloadText(self, url, data = None, filetype = 'auto'):
                ''' Downloads the given url and return the subtitle file as a string.
                    If url points to a compressed file, it will attempt to decompress it
                    and return the subtitle file inside. '''

                # try to see whether we just downloaded a gz or zip file, and if we did, extract it
                result = self._downloadText(url, data)
                zfile = StringIO.StringIO(result)

                if filetype in ('auto', 'gz', 'gzip'):
                        try:
                                f = gzip.GzipFile(fileobj = zfile)
                                result = f.read()
                                f.close()
                                return result
                        except IOError:
                                pass

                if filetype in ('auto', 'zip'):
                        try:
                                zf = zipfile.ZipFile(zfile, 'r')
                                for el in zf.infolist():
                                        print el.orig_filename
                                        extension = el.orig_filename.rsplit(".", 1)[1]
                                        if extension in guessit.patterns.subtitle_exts:
                                                result = zf.read(el.orig_filename)
                                                zf.close()
                                                return result
                        except zipfile.BadZipfile:
                                pass

                if filetype in ('rar',):
                        # TODO: implement me
                        pass

                # not a compressed file, just return the file as is
                return result


	@abc.abstractmethod
	def list(self, filenames, languages):
		''' Main method to call when you want to list subtitles '''

	@abc.abstractmethod
	def download(self, subtitle):
		''' Main method to call when you want to download a subtitle '''

	def getRevertLanguage(self, language):
		''' Returns the short (two-character) representation from the long language name '''
		try:
			return self.revertPluginLanguages[language]
		except KeyError, e:
			self.logger.warn("Ooops, you found a missing language in the configuration file of %s: %s. Send a bug report to have it added." % (self.getClassName(), language))

	def checkLanguages(self, languages):
		if languages and not set(languages).intersection((self._plugin_languages.values())):
			self.logger.debug('None of requested languages %s are available' % languages)
			return False
		return True

	def getLanguage(self, language):
		''' Returns the long naming of the language from a two character code '''
		try:
			return self.pluginLanguages[language]
		except KeyError, e:
			self.logger.warn("Ooops, you found a missing language in the configuration file of %s: %s. Send a bug report to have it added." % (self.getClassName(), language))

	def getExtension(self, subtitle):
		if self.config_dict and self.config_dict['multi']:
			return ".%s.srt" % subtitle['lang']
		return ".srt"

	def getClassName(self):
		return self.__class__.__name__

	def splitTask(self, task):
		''' Determines if the plugin can handle multi-thing queries and output splited tasks for list task only '''
		if task['task'] != 'list':
			return [task]
		tasks = [task]
		if not self.multi_filename_queries:
			tasks = self._splitOnField(tasks, 'filenames')
		if not self.multi_languages_queries:
			tasks = self._splitOnField(tasks, 'languages')
		return tasks

	@staticmethod
	def _splitOnField(elements, field):
		''' Split a list of dict in a bigger one if the element field in the dict has multiple elements too
			i.e. [{'a': 1, 'b': [2,3]}, {'a': 7, 'b': [4]}] => [{'a': 1, 'b': [2]}, {'a': 1, 'b': [3]}, {'a': 7, 'b': [4]}]
			with field = 'b' '''
		results = []
		for e in elements:
			for v in e[field]:
				newElement = {}
				for (key, value) in e.items():
					if key != field:
						newElement[key] = value
					else:
						newElement[key] = [v]
				results.append(newElement)
		return results

	def listTeams(self, sub_teams, separators):
		''' List teams of a given string using separators '''
		for sep in separators:
			sub_teams = self.splitTeam(sub_teams, sep)
		return set(sub_teams)

	def splitTeam(self, sub_teams, sep):
		''' Split teams of a given string using separators '''
		teams = []
		for t in sub_teams:
			teams += t.split(sep)
		return teams
