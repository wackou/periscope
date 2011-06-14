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
import PluginBase
import zipfile
import os
import urllib2
import urllib
import logging
import traceback
import httplib
import re

class SubsWiki(PluginBase.PluginBase):
    site_url = 'http://www.subswiki.com'
    site_name = 'SubsWiki'
    server_url = 'http://www.subswiki.com' # for testing purpose, use http://sandbox.thesubdb.com instead
    multi_languages_queries = True
    multi_filename_queries = False
    api_based = True
    user_agent = 'SubDB/1.0 (Periscope-ng/0.1; https://github.com/Diaoul/periscope-ng/)' # format defined by the API
    _plugin_languages = {u"English (US)": "en",
            u"English (UK)": "en",
            u"English": "en",
            u"French": "fr",
            u"Brazilian": "pt-br",
            u"Portuguese": "pt",
            u"Español (Latinoamérica)": "es",
            u"Español (España)": "es",
            u"Español": "es",
            u"Italian": "it",
            u"Català": "ca"}

    def __init__(self, config_dict=None):
        super(TheSubDB, self).__init__(self._plugin_languages, config_dict, True)
        self.release_pattern = re.compile("\nVersion (.+), ([0-9]+).([0-9])+ MBs")

    def list(self, filepath, languages):
        ''' Main method to call when you want to list subtitles '''
        # as self.multi_filename_queries is false, we won't have multiple filenames in the list so pick the only one
        # once multi-filename queries are implemented, set multi_filename_queries to true and manage a list of multiple filenames here
        if not self.checkLanguages(languages):
            return []
        filepath = filenames[0]
        guess = guessit.guess_file_info(filepath, 'autodetect')
        if guess['type'] != 'episode':
            return []
        # add multiple things to the release group set
        release_group = set()
        if 'releaseGroup' in guess:
            release_group.add(guess['releaseGroup'])
        else:
            if 'title' in guess: 
                release_group.add(guess['title'])
            if 'screenSize' in guess:
                release_group.add(guess['screenSize'])
        if len(release_group) == 0:
            return []
        self.release_group = release_group # used to sort results
        return self.query(guess['series'], guess['season'], guess['episodeNumber'], release_group, filepath, languages)
   
    def query(self, name, season, episode, release_group, filepath, languages=None):
        ''' Make a query and returns info about found subtitles '''
        sublinks = []
        searchname = name.lower().replace(" ", "_")
        searchurl = "%s/serie/%s/%s/%s/" %(self.host, searchname, season, episode)
        self.logger.debug("Searching in %s" %searchurl)
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
        for subs in soup("td", {"class": "NewsTitle"}):
            sub_teams = self.listTeams([self.release_pattern.search("%s" % subs.contents[1]).group(1)], [".", "_", " ", "/"])
            if not release_group.intersection(sub_teams): # On wrong team
                continue
            self.logger.debug("Team from website: %s" % sub_teams)
            self.logger.debug("Team from file: %s" % release_group)
            for html_language in subs.parent.parent.findAll("td", {"class": "language"}):
                sub_language = self.getRevertLanguage(html_language.string.strip())
                if languages and not sub_language in languages: # On wrong language
                    continue
                html_status = html_language.findNextSibling('td')
                sub_status = html_status.find('strong').string.strip()
                if not sub_status == 'Completed': # On not completed subtitles
                    continue
                link = html_status.findNext("td").find("a")["href"]

                if status == "Completed" and subteams.issubset(teams) and (not langs or lang in langs) :
                    result = {}
                    result["release"] = "%s.S%.2dE%.2d.%s" %(name.replace(" ", "."), int(season), int(episode), '.'.join(subteams))
                    result["lang"] = language
                    result["link"] = self.server_url + link
                    result["page"] = searchurl
                    sublinks.append(result)
        return sublinks
       
    def listTeams(self, subteams, separators):
        teams = []
        for sep in separators:
            subteams = self.splitTeam(subteams, sep)
        logging.debug(subteams)
        return set(subteams)
   
    def splitTeam(self, subteams, sep):
        teams = []
        for t in subteams:
            teams += t.split(sep)
        return teams

    def createFile(self, subtitle):
        '''pass the URL of the sub and the file it matches, will unzip it
        and return the path to the created file'''
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtbasefilename = videofilename.rsplit(".", 1)[0]
        srtfilename = srtbasefilename +".srt"
        self.downloadFile(suburl, srtfilename)
        return srtfilename

    def downloadFile(self, url, filename):
        ''' Downloads the given url to the given filename '''
        req = urllib2.Request(url, headers={'Referer' : url, 'User-Agent' : 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3)'})
       
        f = urllib2.urlopen(req)
        dump = open(filename, "wb")
        dump.write(f.read())
        dump.close()
        f.close()

