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

from BeautifulSoup import BeautifulSoup
import guessit
import PluginBase
import zipfile
import os
import urllib2
import urllib
import traceback
import httplib
import re
import socket

class Addic7ed(PluginBase.PluginBase):
    site_url = 'http://www.addic7ed.com'
    site_name = 'Addic7ed'
    server_url = 'http://www.addic7ed.com'
    multi_languages_queries = True
    multi_filename_queries = False
    api_based = False
    _plugin_languages = {u"English": "en",
            u"English (US)": "en",
            u"English (UK)": "en",
            u"Italian": "it",
            u"Portuguese": "pt",
            u"Portuguese (Brazilian)": "pt-br",
            u"Romanian": "ro",
            u"Español (Latinoamérica)": "es",
            u"Español (España)": "es",
            u"Spanish (Latin America)": "es",
            u"Español": "es",
            u"Spanish": "es",
            u"Spanish (Spain)": "es",
            u"French": "fr",
            u"Greek": "el",
            u"Arabic": "ar",
            u"German": "de",
            u"Croatian": "hr",
            u"Indonesian": "id",
            u"Hebrew": "he",
            u"Russian": "ru",
            u"Turkish": "tr",
            u"Swedish": "se",
            u"Czech": "cs",
            u"Dutch": "nl",
            u"Hungarian": "hu",
            u"Norwegian": "no",
            u"Polish": "pl",
            u"Persian": "fa"}

    def __init__(self, config_dict=None):
        super(Addic7ed, self).__init__(self._plugin_languages, config_dict, isRevert=True)
        #http://www.addic7ed.com/serie/Smallville/9/11/Absolute_Justice
        self.release_pattern = re.compile(" \nVersion (.+), ([0-9]+).([0-9])+ MBs")

    def list(self, filenames, languages):
        ''' Main method to call when you want to list subtitles '''
        # as self.multi_filename_queries is false, we won't have multiple filenames in the list so pick the only one
        # once multi-filename queries are implemented, set multi_filename_queries to true and manage a list of multiple filenames here
        filepath = filenames[0]
        fname = unicode(self.getFileName(filepath).lower())
        guess = guessit.guess_file_info(filepath, 'autodetect')
        self.logger.debug(guess.nice_string())
        if guess['type'] == 'episode':
            return self.query(guess['series'], guess['season'], guess['episodeNumber'], guess['releaseGroup'], filepath, languages)
        else:
            return []

    def query(self, name, season, episode, team, filepath, languages=None):
        ''' Make a query and returns info about found subtitles '''
        searchname = name.lower().replace(" ", "_")
        searchurl = "%s/serie/%s/%s/%s/%s" % (self.server_url, searchname, season, episode, searchname)
        self.logger.debug("Searching in %s" % searchurl)
        try:
            req = urllib2.Request(searchurl, headers={'User-Agent': self.user_agent})
            page = urllib2.urlopen(req, timeout=self.timeout)
        except urllib2.HTTPError as inst:
            self.logger.info("Error: %s - %s" % (searchurl, inst))
            return []
        except urllib2.URLError as inst:
            self.logger.info("TimeOut: %s" % inst)
            return []
        soup = BeautifulSoup(page.read())
        sublinks = []
        for html_sub in soup("td", {"class": "NewsTitle", "colspan": "3"}):
            if not self.release_pattern.match(str(html_sub.contents[1])): # On not needed soup td result
                continue
            sub_teams = self.listTeams([self.release_pattern.match(str(html_sub.contents[1])).groups()[0]], [".", "_", " "])
            if not team in sub_teams: # On wrong team
                continue
            html_language = html_sub.findNext("td", {"class" : "language"})
            sub_language = self.getRevertLanguage(html_language.contents[0].strip().replace('&nbsp;', ''))
            if languages and  not sub_language in languages: # On wrong language
                continue
            html_status = html_language.findNextSibling('td')
            sub_status = html_status.find('b').string.strip()
            if not sub_status == 'Completed': # On not completed subtitles
                continue
            sub_link = self.server_url + html_status.findNextSibling('td', {'colspan': '3'}).find('a')['href']
            self.logger.debug('Found a match with teams: %s' % sub_teams)
            result = {}
            result["release"] = "%s.S%.2dE%.2d.%s" % (name.replace(" ", "."), int(season), int(episode), '.'.join(sub_teams))
            result["lang"] = sub_language
            result["link"] = sub_link
            result["page"] = searchurl
            result["filename"] = filepath
            result["plugin"] = self.getClassName()
            sublinks.append(result)
        return sublinks

    def listTeams(self, subteams, separators):
        for sep in separators:
            subteams = self.splitTeam(subteams, sep)
        return subteams

    def splitTeam(self, subteams, sep):
        teams = []
        for t in subteams:
            teams += t.split(sep)
        return teams

    def download(self, subtitle):
        '''pass the URL of the sub and the file it matches, will unzip it
        and return the path to the created file'''
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtbasefilename = videofilename.rsplit(".", 1)[0]
        srtfilename = srtbasefilename + self.getExtension(subtitle)
        self.downloadFile(suburl, srtfilename)
        return srtfilename
