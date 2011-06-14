import unittest
import logging
import os

logging.basicConfig(level=logging.DEBUG, format='%(name)-24s %(levelname)-8s %(message)s')
config = {'multi': True, 'cache_dir': '/tmp/periscope/cache', 'subtitlesource_key': '', 'force': False}

class Addic7edListTestCase1(unittest.TestCase):
    def runTest(self):
        import Addic7ed
        plugin = Addic7ed.Addic7ed(config)
        results = plugin.list(["The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ["en", "fr"])
        print results
        assert len(results) > 0

class Addic7edListTestCase2(unittest.TestCase):
    def runTest(self):
        import Addic7ed
        plugin = Addic7ed.Addic7ed(config)
        results = plugin.list(["Dexter.S05E02.720p.HDTV.x264-IMMERSE.mkv"], ["en", "fr"])
        print results
        assert len(results) > 0

class Addic7edDownloadTestCase(unittest.TestCase):
    def runTest(self):
        import Addic7ed
        plugin = Addic7ed.Addic7ed(config)
        results = plugin.download(plugin.list(["/tmp/The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ["en", "fr"])[0])
        print results
        assert len(results) > 0

class BierDopjeListTestCase(unittest.TestCase):
    def runTest(self):
        import BierDopje
        plugin = BierDopje.BierDopje(config)
        results = plugin.list(["The.Office.US.S07E08.Viewing.Party.HDTV.XviD-FQM.[VTV].avi"], ["en", "fr"])
        print results
        assert len(results) > 0

class OpenSubtitlesQueryTestCase(unittest.TestCase):
    def runTest(self):
        import OpenSubtitles
        plugin = OpenSubtitles.OpenSubtitles()
        results = plugin.query('Night.Watch.2004.CD1.DVDRiP.XViD-FiCO.avi', moviehash="09a2c497663259cb", bytesize="733589504") # http://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC
        print results
        assert len(results) > 0

class OpenSubtitlesListTestCase(unittest.TestCase):
    def runTest(self):
        import OpenSubtitles
        plugin = OpenSubtitles.OpenSubtitles()
        results = plugin.download(plugin.query('/tmp/Night.Watch.2004.CD1.DVDRiP.XViD-FiCO.avi', moviehash="09a2c497663259cb", bytesize="733589504")[0]) # http://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC
        assert len(results) > 0

class PodnapisiQueryTestCase(unittest.TestCase):
    def runTest(self):
        import Podnapisi
        plugin = Podnapisi.Podnapisi()
        results = plugin.query('09a2c497663259cb', ["en", "fr"])
        print results
        assert len(results) > 5

class SubSceneListTestCase(unittest.TestCase):
    def runTest(self):
        import SubScene
        plugin = SubScene.SubScene()
        results = plugin.list(["Dexter.S04E01.HDTV.XviD-NoTV.avi"], ['en', 'fr'])
        print results
        assert len(results) > 0, "No result could be found for Dexter.S04E01.HDTV.XviD-NoTV.avi and no languages"

class SubSceneDownloadTestCase(unittest.TestCase):
    def runTest(self):
        import SubScene
        plugin = SubScene.SubScene()
        results = plugin.download(plugin.list(["Dexter.S04E01.HDTV.XviD-NoTV.avi"], ['en', 'fr'])[0])
        print results
        assert len(results) > 0, "No result could be found for Dexter.S04E01.HDTV.XviD-NoTV.avi and no languages"

class SubtitleSourceListTestCase(unittest.TestCase):
    def runTest(self):
        import SubtitleSource
        plugin = SubtitleSource.SubtitleSource()
        results = plugin.list(["PrisM-Inception.2010"], ['en', 'fr'])
        print results
        assert len(results) > 0, "No result could be found for PrisM-Inception.2010"

class SubtitulosListTestCase(unittest.TestCase):
    def runTest(self):
        import Subtitulos
        plugin = Subtitulos.Subtitulos()
        results = plugin.list(["The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ['en', 'fr'])
        print results
        assert len(results) > 0

class SubtitulosDownloadTestCase(unittest.TestCase):
    def runTest(self):
        import Subtitulos
        plugin = Subtitulos.Subtitulos()
        results = plugin.download(plugin.list(["/tmp/The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ['en', 'fr'])[0])
        print results
        assert len(results) > 0

class TheSubDBQueryTestCase(unittest.TestCase):
    def runTest(self):
        import TheSubDB
        plugin = TheSubDB.TheSubDB()
        results = plugin.query("test.mkv", "edc1981d6459c6111fe36205b4aff6c2")
        print results
        assert len(results) > 0

class TheSubDBDownloadTestCase(unittest.TestCase):
    def runTest(self):
        import TheSubDB
        plugin = TheSubDB.TheSubDB()
        results = plugin.download(plugin.query("/tmp/test.mkv", "edc1981d6459c6111fe36205b4aff6c2")[0])
        print results
        assert len(results) > 0

class SubsWikiListTestCase(unittest.TestCase):
    def runTest(self):
        import Subtitulos
        plugin = Subtitulos.Subtitulos()
        results = plugin.list(["The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ['en', 'fr'])
        print results
        assert len(results) > 0

class SubsWikiDownloadTestCase(unittest.TestCase):
    def runTest(self):
        import Subtitulos
        plugin = Subtitulos.Subtitulos()
        results = plugin.download(plugin.list(["/tmp/The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ['en', 'fr'])[0])
        print results
        assert len(results) > 0
'''
class TvSubtitlesTestCase(unittest.TestCase):
    def runTest(self):
        import TvSubtitles
        plugin = TvSubtitles.TvSubtitles()
        fname = "The.Big.Bang.Theory.S03E15.The.Large.Hadron.Collision.HDTV.XviD-FQM"
        guessedData = plugin.guessFileData(fname)
        subs = plugin.query(guessedData['name'], guessedData['season'], guessedData['episode'], guessedData['teams'], ['en'])
        for s in subs:
            print "Sub : %s" %s
'''


if __name__ == "__main__":
    unittest.main()
