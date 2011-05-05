#!/usr/bin/python
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

from itertools import groupby
import ConfigParser
import PluginWorker
import Queue
import locale
import logging
import mimetypes
import os
import plugins
import sys
import traceback

SUPPORTED_FORMATS = 'video/x-msvideo', 'video/quicktime', 'video/x-matroska', 'video/mp4'

class Periscope(object):
    ''' Main Periscope class'''

    def __init__(self, config=True, cache_dir=True, workers=4, multi=False, force=False, max_depth=3, autostart=True):
        # set default values
        self.multi = multi
        self.force = force
        self.max_depth = max_depth
        self.config = None
        self.config_file = None
        self.cache_dir = None
        self.taskQueue = Queue.Queue()
        self.resultQueue = Queue.Queue()
        self._languages = None
        self._plugins = self.listAPIPlugins()
        self.workers = workers
        self.logger = logging.getLogger('periscope')
        if autostart:
            self.startWorkers()
        # handle configuration file preferences
        try:
            if config == True: # default configuration file
                import xdg.BaseDirectory as bd
                self.config = ConfigParser.SafeConfigParser({"languages": "", "plugins": "" })
                self.config_file = os.path.join(bd.xdg_config_home, "periscope", "config.ini")
                if not os.path.exists(self.config_file): # configuration file doesn't exist, create it
                    self._createConfigFile()
                else: # configuration file exists, load it
                    self._loadConfigFile()
            elif config: # custom configuration file
                self.config = ConfigParser.SafeConfigParser({"languages": "", "plugins": "" })
                self.config_file = config
                if not os.path.isfile(self.config_file): # custom configuration file doesn't exist, create it
                    self._createConfigFile()
                else:
                    self._loadConfigFile()
        except:
            self.config = None
            self.config_file = None
            self.logger.error("Failed to use the configuration file, continue without it")
            raise
        # handle cache directory preferences
        try:
            if cache_dir == True: # default cache directory
                import xdg.BaseDirectory as bd
                self.cache_dir = os.path.join(bd.xdg_config_home, "periscope", "cache")
                if not os.path.exists(self.cache_dir): # cache directory doesn't exist, create it
                    os.mkdir(self.cache_dir)
                    self.logger.debug('Creating cache directory: %s' % self.cache_dir)
            elif cache_dir: # custom configuration file
                self.cache_dir = cache_dir
                if not os.path.isdir(self.cache_dir): # custom v file doesn't exist, create it
                    os.mkdir(self.cache_dir)
                    self.logger.debug('Creating cache directory: %s' % self.cache_dir)
        except:
            self.cache_dir = None
            self.logger.error("Failed to use the cache directory, continue without it")
    
    def _loadConfigFile(self):
        ''' Load a configuration file specified in self.config_file '''
        self.config.read(self.config_file)
        self._loadLanguagesFromConfig()
        self._loadPluginsFromConfig()
            
    def _createConfigFile(self):
        ''' Create a configuration file specified in self.config_file '''
        folder = os.path.dirname(self.config_file)
        if not os.path.exists(folder):
            self.logger.info("Creating folder: %s" % folder)
            os.mkdir(folder)
        # try to load a language from system
        self._loadLanguageFromSystem()
        self.config.set("DEFAULT", "languages", ",".join(self._languages))
        self.config.set("DEFAULT", "plugins", ",".join(self._plugins))
        self.config.add_section("SubtitleSource")
        self.config.set("SubtitleSource", "key", "")
        self._writeConfigFile()
        self.logger.info("Creating configuration file: %s" % self.config_file)
        self.logger.debug("Languages in created configuration file: %s" % self._languages)
        self.logger.debug("Plugins in created configuration file: %s" % self._plugins)

    @staticmethod
    def listExistingPlugins():
        ''' List all possible plugins '''
        return map(lambda x: x.__name__, plugins.PluginBase.PluginBase.__subclasses__())

    @staticmethod
    def listAPIPlugins():
        ''' List plugins that use API '''
        return filter(Periscope.isAPIBasedPlugin, Periscope.listExistingPlugins())

    def _writeConfigFile(self):
        ''' Write the configuration file '''
        configfile = open(self.config_file, "w")
        self.config.write(configfile)
        configfile.close()

    def get_languages(self):
        ''' Get current languages '''
        return self._languages

    def set_languages(self, value):
        ''' Set languages and save to configuration file if specified by the constructor '''
        self.logger.debug("Setting languages to %s" % value)
        self._languages = value
        if self.config:
            self._saveLanguagesToConfig()

    def isValidLanguage(self, language):
        ''' Check if a language is valid '''
        if len(language) != 2:
            self.logger.error("Language %s is not valid" % language)
            return False
        return True

    def _saveLanguagesToConfig(self):
        ''' Save languages to configuration file '''
        self.logger.debug("Saving languages %s to configuration file" % self._languages)
        self.config.set("DEFAULT", "languages", ",".join(self._languages))
        self._writeConfigFile()

    def _loadLanguagesFromConfig(self):
        ''' Load languages from configuration file '''
        configLanguages = self.config.get("DEFAULT", "languages")
        self.logger.debug("Loading languages %s from configuration file" % configLanguages)
        if not configLanguages:
            self._languages = None
            return
        self._languages = filter(self.isValidLanguage, map(str.strip, configLanguages.split(",")))

    def _loadLanguageFromSystem(self):
        ''' Load language from system '''
        self.logger.debug("Loading language from system")
        try:
            self._languages = [locale.getdefaultlocale()[0][:2]]
            self.logger.debug("Language %s loaded from system" % self._languages)
        except:
            self.logger.warning("Could not read language from system")

    def get_plugins(self):
        ''' Get current plugins '''
        return self._plugins

    def set_plugins(self, value):
        ''' Set plugins and save to configuration file if specified by the constructor '''
        self.logger.debug("Setting plugins to %s" % value)
        self._plugins = filter(self.isValidPlugin, value)
        if self.config:
            self._savePluginsToConfig()

    def isValidPlugin(self, pluginName):
        ''' Check if a plugin is valid (exists) '''
        if pluginName not in self.listExistingPlugins():
            self.logger.error("Plugin %s does not exist" % pluginName)
            return False
        return True

    @staticmethod
    def isAPIBasedPlugin(pluginName):
        ''' Check if a plugin is API-based '''
        if not getattr(plugins, pluginName).api_based:
            return False
        return True

    def _savePluginsToConfig(self):
        ''' Save plugins to configuration file '''
        self.logger.debug("Saving plugins %s to configuration file" % self._plugins)
        self.config.set("DEFAULT", "plugins", ",".join(self._plugins))
        self._writeConfigFile

    def _loadPluginsFromConfig(self):
        ''' Load plugins from configuration file '''
        configPlugins = self.config.get("DEFAULT", "plugins")
        self.logger.debug("Loading plugins %s from configuration file" % configPlugins)
        self._plugins = filter(self.isValidPlugin, map(str.strip, configPlugins.split(",")))

    # getters/setters for the property _languages and _plugins
    languages = property(get_languages, set_languages)
    plugins = property(get_plugins, set_plugins)

    def deactivatePlugin(self, plugin):
        ''' Deactivate a plugin '''
        self._plugins.remove(plugin)
        if self.config:
            self._savePluginsToConfig()

    def activatePlugin(self, plugin):
        ''' Activate a plugin '''
        if self.isValidPlugin(plugin):
            self._plugins.append(plugin)
        if self.config:
            self._savePluginsToConfig()

    def listSubtitles(self, entries):
        ''' Searches subtitles within the active plugins and returns all found matching subtitles.
        entries can be:
            - filepaths
            - folderpaths (N.B. internal recursive search function will be used)
            - filenames '''
        search_results = []
        for e in entries:
            search_results.extend(self._recursiveSearch(e))
        taskCount = 0
        for (l, f) in search_results:
            taskCount += self._searchSubtitles(f, l)
        subtitles = []
        for i in range(taskCount):
            subtitles.extend(self.resultQueue.get(timeout=10))
        return subtitles

    @staticmethod
    def arrangeSubtitles(subtitles):
        ''' Arrange subtitles in a handy dict by filename, language and plugin '''
        arrangedSubtitles = {}
        for (filename, subsByFilename) in groupby(sorted(subtitles, key=lambda x: x["filename"]), lambda x: x["filename"]):
            arrangedSubtitles[filename] = {}
            for (language, subsByFilenameByLanguage) in groupby(sorted(subsByFilename, key=lambda x: x["lang"]), lambda x: x["lang"]):
                arrangedSubtitles[filename][language] = {}
                for (plugin, subsByFilenameByLanguageByPlugin) in groupby(sorted(subsByFilenameByLanguage, key=lambda x: x["plugin"]), lambda x: x["plugin"]):
                    arrangedSubtitles[filename][language][plugin] = sorted(list(subsByFilenameByLanguageByPlugin))
        return arrangedSubtitles

    def sortSubtitlesRaw(self, subtitles):
        ''' Sort subtitles using user defined languages and plugins '''
        return sorted(subtitles, cmp=self._cmpSubtitles)

    def _cmpSubtitles(self, x, y):
        ''' Compares 2 subtitles elements x and y. Returns -1 if x < y, 0 if =, 1 if >
            Use filename, languages and plugin comparison '''
        filenames = sorted([x['filename'], y['filename']])
        if x['filename'] != y['filename'] and filenames.index(x['filename']) < filenames(y['filename']):
            return - 1
        if x['filename'] != y['filename'] and filenames.index(x['filename']) > filenames(y['filename']):
            return 1
        if self._languages and self._languages.index(x['lang']) < self._languages.index(y['lang']):
            return - 1
        if self._languages and self._languages.index(x['lang']) > self._languages.index(y['lang']):
            return 1
        if self._plugins.index(x['plugin']) < self._plugins.index(y['plugin']):
            return - 1
        if self._plugins.index(x['plugin']) > self._plugins.index(y['plugin']):
            return 1
        return 0

    def _searchSubtitles(self, filenames, languages):
        ''' Makes workers search for subtitles in different languages for multiple filenames and puts the result in the result queue.
            Aslo split the work in multiple tasks
            When the function returns, all the results may not be available yet! '''
        self.logger.info("Searching subtitles for %s with languages %s" % (filenames, languages))
        tasks = []
        for pluginName in self._plugins:
            try:
                plugin = getattr(plugins, pluginName)(self)
            except:
                self.logger.debug(traceback.print_exc())
                continue
            # split tasks if the plugin can't handle multi-thing queries
            tasks.extend(plugin.splitTask({'task': 'list', 'plugin': pluginName, 'languages': languages, 'filenames': filenames, 'periscope': self}))
        for t in tasks:
            self.taskQueue.put(t)
        return len(tasks)

    def _downloadSubtitles(self, subtitles):
        ''' Makes workers download subtitles and puts the result in the result queue.
            When the function returns, all the results may not be available yet! '''
        # 1 task per file if not multi, 1 task per file and per language if multi
        taskCount = 0
        for (filename, subsByFilename) in groupby(sorted(subtitles, key=lambda x: x["filename"]), lambda x: x["filename"]):
            if not self.multi:
                self.taskQueue.put({'task': 'download', 'subtitle': sorted(list(subsByFilename), cmp=self._cmpSubtitles), 'periscope': self})
                taskCount += 1
                continue
            for (language, subsByFilenameByLanguage) in groupby(sorted(subsByFilename, key=lambda x: x["lang"]), lambda x: x["lang"]):
                self.taskQueue.put({'task': 'download', 'subtitle': sorted(list(subsByFilenameByLanguage), cmp=self._cmpSubtitles), 'periscope': self})
                taskCount += 1
        return taskCount

    def downloadSubtitles(self, entries):
        ''' Download subtitles recursivly in entries '''
        subtitles = self.listSubtitles(entries)
        taskCount = self._downloadSubtitles(subtitles)
        paths = []
        for i in range(taskCount):
            paths.append(self.resultQueue.get(timeout=10))
        return paths

    def _recursiveSearch(self, entry, depth=0):
        ''' Searches files in the entry
            This will output a list of tuples (filename, languages) '''
        if depth > self.max_depth and self.max_depth != 0: # we do not want to search the whole file system except if max_depth = 0
            return []
        if os.path.isfile(entry): # a file? scan it
            if depth != 0: # only check for valid format if recursing, trust the user
                mimetypes.add_type("video/x-matroska", ".mkv")
                mimetype = mimetypes.guess_type(entry)[0]
                if mimetype not in SUPPORTED_FORMATS:
                    return []
            basepath = os.path.splitext(entry)[0]
            # check for .xx.srt if needed
            if self.languages:
                if self.force:
                    return [(self.languages, [os.path.normpath(entry)])]
                needed_languages = self.languages[:]
                for l in self.languages:
                    if os.path.exists(basepath + '.%s.srt' % l):
                        self.logger.info("Skipping language %s for file %s as it already exists. Use the --force option to force the download" % (l, entry))
                        needed_languages.remove(l)
                if needed_languages:
                    return [(needed_languages, [os.path.normpath(entry)])]
                return []
            # single subtitle download: .srt
            if self.force or not os.path.exists(basepath + '.srt'):
                return [(None, [os.path.normpath(entry)])]
        if os.path.isdir(entry): # a dir? recurse
            #TODO if hidden folder, don't keep going (how to handle windows/mac/linux ?)
            files = []
            for e in os.listdir(entry):
                files.extend(self._recursiveSearch(os.path.join(entry, e), depth + 1))
            files.sort()
            grouped_files = []
            for languages, group in groupby(files, lambda t: t[0]):
                filenames = []
                for t in group:
                    filenames.extend(t[1])
                grouped_files.append((languages, filenames)) 
            return grouped_files
        return [] # anything else, nothing.

    def startWorkers(self):
        ''' Create a pool of workers and start them '''
        self.pool = []
        for i in range(self.workers):
            worker = PluginWorker.PluginWorker(self.taskQueue, self.resultQueue)
            worker.start()
            self.pool.append(worker)
            self.logger.debug("Worker %s added to the pool" % worker.name)

    def stopWorkers(self):
        ''' Stop the pool of workers using a death event (poison pill) and wait for them to terminate properly '''
        self.logger.debug("Sending %d poison pills into the task queue" % self.workers)
        for i in range(self.workers):
            self.taskQueue.put(None)
        for worker in self.pool:
            worker.join()
