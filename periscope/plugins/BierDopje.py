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

from xml.dom import minidom
import guessit
import PluginBase
import os
import pickle
import traceback
import urllib
import urllib2

class BierDopje(PluginBase.PluginBase):
    site_url = 'http://bierdopje.com'
    site_name = 'BierDopje'
    server_url = 'http://api.bierdopje.com/112C8204D6754A2A/'
    multi_languages_queries = True
    multi_filename_queries = False
    api_based = True
    exceptions = {'the office': 10358,
        'the office us': 10358,
        'greys anatomy': 3733,
        'sanctuary us': 7904,
        'human target 2010': 12986,
        'csi miami': 2187,
        'castle 2009': 12708,
        'chase 2010': 14228,
        'the defenders 2010': 14225,
        'hawaii five-0 2010': 14211}
    _plugin_languages = {'en': 'en', 'nl': 'nl'}

    def __init__(self, config_dict):
        super(BierDopje, self).__init__(self._plugin_languages, config_dict)
        #http://api.bierdopje.com/23459DC262C0A742/GetShowByName/30+Rock
        #http://api.bierdopje.com/23459DC262C0A742/GetAllSubsFor/94/5/1/en (30 rock, season 5, episode 1)
        if not config_dict or not config_dict['cache_dir']:
             raise Exception('Cache directory is mandatory for this plugin')
        self.showid_cache = os.path.join(config_dict['cache_dir'], "bierdopje_showid.cache")
        with self.lock:
            if not os.path.exists(self.showid_cache):
                f = open(self.showid_cache, 'w')
                pickle.dump({}, f)
                f.close()
            f = open(self.showid_cache, 'r')
            self.showids = pickle.load(f)
            f.close()

    def list(self, filenames, languages):
        ''' Main method to call when you want to list subtitles '''
        # as self.multi_filename_queries is false, we won't have multiple filenames in the list so pick the only one
        # once multi-filename queries are implemented, set multi_filename_queries to true and manage a list of multiple filenames here
        if not self.checkLanguages(languages):
            return []
        filepath = filenames[0]
        guess = guessit.guess_file_info(filepath, 'autodetect')
        if guess['type'] != 'episode':
            return []
        return self.query(guess['series'], guess['season'], guess['episodeNumber'], guess['releaseGroup'], filepath, languages)

    def download(self, subtitle):
        ''' Main method to call when you want to download a subtitle '''
        subpath = subtitle["filename"].rsplit(".", 1)[0] + self.getExtension(subtitle)
        self.downloadFile(subtitle["link"], subpath)
        return subpath

    def query(self, name, season, episode, releaseGroup, filepath, languages=None):
        ''' Makes a query and returns info (link, lang) about found subtitles '''
        if languages:
            available_languages = list(set(languages).intersection((self._plugin_languages.values())))
        else:
            available_languages = self._plugin_languages.values()
        sublinks = []

        # get the show id
        show_name = name.lower()
        if show_name in self.exceptions: # get it from exceptions
            show_id = self.exceptions[show_name]
        elif show_name in self.showids: # get it from cache
            show_id = self.showids[show_name]
        else: # retrieve it
            show_id_url = "%sGetShowByName/%s" % (self.server_url, urllib.quote(show_name))
            self.logger.debug("Retrieving show id from web at %s" % show_id_url)
            page = urllib2.urlopen(show_id_url)
            dom = minidom.parse(page)
            if not dom or len(dom.getElementsByTagName('showid')) == 0: # no proper result
                page.close()
                return []
            show_id = dom.getElementsByTagName('showid')[0].firstChild.data
            self.showids[show_name] = show_id
            with self.lock:
                f = open(self.showid_cache, 'w')
                pickle.dump(self.showids, f)
                f.close()
            page.close()

        # get the subs for the show id we have
        for language in available_languages :
            subs_url = "%sGetAllSubsFor/%s/%s/%s/%s" % (self.server_url, show_id, season, episode, language)
            self.logger.debug("Getting subtitles at %s" % subs_url)
            page = urllib2.urlopen(subs_url)
            dom = minidom.parse(page)
            page.close()
            for sub in dom.getElementsByTagName('result'):
                sub_release = sub.getElementsByTagName('filename')[0].firstChild.data
                if sub_release.endswith(".srt"):
                    sub_release = sub_release[:-4]
                sub_release = sub_release + '.avi' # put a random extension for guessit not to fail guessing that file
                sub_guess = guessit.guess_file_info(sub_release, 'episode')
                sub_link = sub.getElementsByTagName('downloadlink')[0].firstChild.data
                if sub_guess['series'] == name and sub_guess['season'] == season and sub_guess['episodeNumber'] == episode and sub_guess['releaseGroup'] == releaseGroup:
                    self.logger.debug("Found a match: %s" % sub_release)
                    result = {}
                    result["release"] = sub_release
                    result["link"] = sub_link
                    result["page"] = sub_link
                    result["lang"] = language
                    result["filename"] = filepath
                    result["plugin"] = self.getClassName()
                    sublinks.append(result)
        return sublinks
