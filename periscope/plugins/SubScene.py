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
import traceback
import httplib

class SubScene(PluginBase.PluginBase):
    site_url = 'http://subscene.com'
    site_name = 'SubScene'
    server_url = 'http://subscene.com/s.aspx?subtitle='
    multi_languages_queries = True
    multi_filename_queries = False
    api_based = False
    _plugin_languages = {"en": "English",
            "se": "Swedish",
            "da": "Danish",
            "fi":"Finnish",
            "no": "Norwegian",
            "fr": "French",
            "es": "Spanish",
            "is": "Icelandic",
            "cs": "Czech",
            "bg": "Bulgarian",
            "de": "German",
            "ar": "Arabic",
            "el": "Greek",
            "fa": "Farsi/Persian",
            "nl": "Dutch",
            "he": "Hebrew",
            "id": "Indonesian",
            "ja": "Japanese",
            "vi": "Vietnamese",
            "pt": "Portuguese",
            "ro": "Romanian",
            "tr": "Turkish",
            "sr": "Serbian",
            "pt-br": "Brazillian Portuguese",
            "ru": "Russian",
            "hr": "Croatian",
            "sl": "Slovenian",
            "zh": "Chinese BG code",
            "it": "Italian",
            "pl": "Polish",
            "ko": "Korean",
            "hu": "Hungarian",
            "ku": "Kurdish",
            "et": "Estonian"}

    def __init__(self, config_dict=None):
        super(SubScene, self).__init__(self._plugin_languages, config_dict)
        #http://subscene.com/s.aspx?subtitle=Dexter.S04E01.HDTV.XviD-NoTV

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
        subpage = subtitle["page"]
        page = urllib2.urlopen(subpage)
        soup = BeautifulSoup(page)
        dlhref = soup.find("div", {"class": "download"}).find("a")["href"]
        subtitle["link"] = self.site_url + dlhref.split('"')[7]
        format = "zip"
        archivefilename = subtitle["filename"].rsplit(".", 1)[0] + '.' + format
        self.downloadFile(subtitle["link"], archivefilename)
        subtitlefilename = None
        if zipfile.is_zipfile(archivefilename):
            self.logger.debug("Unzipping file " + archivefilename)
            zf = zipfile.ZipFile(archivefilename, "r")
            for el in zf.infolist():
                extension = el.orig_filename.rsplit(".", 1)[1]
                if extension in ("srt", "sub", "txt"):
                    subtitlefilename = srtbasefilename + "." + extension
                    outfile = open(subtitlefilename, "wb")
                    outfile.write(zf.read(el.orig_filename))
                    outfile.flush()
                    outfile.close()
                else:
                    self.logger.info("File %s does not seem to be valid " % el.orig_filename)
            # Deleting the zip file
            zf.close()
            os.remove(archivefilename)
            return subtitlefilename
        elif archivefilename.endswith('.rar'):
            self.logger.warn('Rar is not really supported yet. Trying to call unrar')
            import subprocess
            try :
                args = ['unrar', 'lb', archivefilename]
                output = subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]
                for el in output.splitlines():
                    extension = el.rsplit(".", 1)[1]
                    if extension in ("srt", "sub"):
                        args = ['unrar', 'e', archivefilename, el, os.path.dirname(archivefilename)]
                        subprocess.Popen(args)
                        tmpsubtitlefilename = os.path.join(os.path.dirname(archivefilename), el)
                        subtitlefilename = os.path.join(os.path.dirname(archivefilename), srtbasefilename + "." + extension)
                        if os.path.exists(tmpsubtitlefilename):
                            # rename it to match the file
                            os.rename(tmpsubtitlefilename, subtitlefilename)
                            # exit
                        return subtitlefilename
            except OSError, e:
                self.logger.error("Execution failed: %s" % e)
                return None
        else:
            self.logger.info("Unexpected file type (not zip) for %s" % archivefilename)
            return None

    def downloadFile(self, url, filename):
        ''' Downloads the given url to the given filename '''
        #FIXME: Not working
        super(SubScene, self).downloadFile(url, filename, urllib.urlencode({'__EVENTTARGET' : 's$lc$bcr$downloadLink', '__EVENTARGUMENT' : '', '__VIEWSTATE' : '/wEPDwUHNzUxOTkwNWRk4wau5efPqhlBJJlOkKKHN8FIS04='}))

    def query(self, token, filepath, langs=None):
        ''' Make a query on SubScene and returns info about found subtitles '''
        sublinks = []
        searchurl = "%s%s" % (self.server_url, urllib.quote(token))
        self.logger.debug("Query: %s" % searchurl)
        page = urllib2.urlopen(searchurl)
        soup = BeautifulSoup(page.read())
        for subs in soup("a", {"class": "a1"}):
            lang_span = subs.find("span")
            lang = self.getRevertLanguage(lang_span.contents[0].strip())
            release_span = lang_span.findNext("span")
            release = release_span.contents[0].strip().split(" (")[0]
            sub_page = subs["href"]
            #http://subscene.com//s-dlpath-260016/78348/rar.zipx
            if release.lower().startswith(token.lower()) and (not langs or lang in langs):
                result = {}
                result["release"] = release
                result["lang"] = lang
                result["link"] = None
                result["page"] = self.site_url + sub_page
                result["filename"] = filepath
                result["plugin"] = self.getClassName()
                sublinks.append(result)
        return sublinks
