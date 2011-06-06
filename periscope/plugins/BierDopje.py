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

    def __init__(self, periscope=None):
        super(BierDopje, self).__init__(self._plugin_languages, periscope)
        #http://api.bierdopje.com/23459DC262C0A742/GetShowByName/30+Rock
        #http://api.bierdopje.com/23459DC262C0A742/GetAllSubsFor/94/5/1/en (30 rock, season 5, episode 1)
        if not periscope or not periscope.cache_dir:
             raise Exception('Cache directory is mandatory for this plugin')
        self.showid_cache = os.path.join(periscope.cache_dir, "bierdopje_showid.cache")
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
        filepath = filenames[0]
        fname = self.getFileName(filepath)
        subs = self.query(fname, filepath, languages)
        if not subs and fname.rfind(".[") > 0:
            # Try to remove the [VTV] or [EZTV] at the end of the file
            teamless_filename = fname[0 : fname.rfind(".[")]
            subs = self.query(teamless_filename, filepath, languages)
            return subs
        else:
            return subs

    def download(self, subtitle):
        ''' Main method to call when you want to download a subtitle '''
        subpath = subtitle["filename"].rsplit(".", 1)[0] + self.getExtension(subtitle)
        self.downloadFile(subtitle["link"], subpath)
        return subpath

    def query(self, token, filepath, languages=None):
        ''' Makes a query and returns info (link, lang) about found subtitles '''
        guessedData = self.guessFileData(token)
        self.logger.debug("Data: %s" % guessedData)
        if guessedData['type'] != "tvshow":
            return []
        elif languages and not set(languages).intersection((self._plugin_languages.values())):
            return []
            
        if not languages :
            available_languages = self._plugin_languages.values()
        else :
            available_languages = list(set(languages).intersection((self._plugin_languages.values())))
        sublinks = []
        # query the show to get the show id
        showName = guessedData['name'].lower()
        if self.exceptions.has_key(showName):
            show_id = self.exceptions.get(showName)
        elif self.showids.has_key(showName):
            show_id = self.showids.get(showName)
        else :
            getShowId_url = "%sGetShowByName/%s" % (self.server_url, urllib.quote(showName))
            self.logger.debug("Looking for show id %s" % getShowId_url)
            page = urllib2.urlopen(getShowId_url)
            dom = minidom.parse(page)
            if not dom or len(dom.getElementsByTagName('showid')) == 0 :
                page.close()
                return []
            show_id = dom.getElementsByTagName('showid')[0].firstChild.data
            self.showids[showName] = show_id
            with self.lock:
                f = open(self.showid_cache, 'w')
                pickle.dump(self.showids, f)
                f.close()
            page.close()
        # query the episode to get the subs
        for lang in available_languages :
            getAllSubs_url = "%sGetAllSubsFor/%s/%s/%s/%s" % (self.server_url, show_id, guessedData['season'], guessedData['episode'], lang)
            self.logger.debug("BierDopje looking for subtitles %s" % getAllSubs_url)
            page = urllib2.urlopen(getAllSubs_url)
            dom = minidom.parse(page)
            page.close()
            for sub in dom.getElementsByTagName('result'):
                release = sub.getElementsByTagName('filename')[0].firstChild.data
                if release.endswith(".srt"):
                    release = release[:-4]
                dllink = sub.getElementsByTagName('downloadlink')[0].firstChild.data
                self.logger.debug("Release %s found while searching for %s" % (release.lower(), token.lower()))
                if release.lower() == token.lower():
                    result = {}
                    result["release"] = release
                    result["link"] = dllink
                    result["page"] = dllink
                    result["lang"] = lang
                    result["filename"] = filepath
                    result["plugin"] = self.getClassName()
                    sublinks.append(result)
        return sublinks
