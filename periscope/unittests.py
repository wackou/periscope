#!/usr/bin/env python
# -*- coding: utf-8 -*-


from unittest import *
import os, sys
import periscope
import chardet
import logging

log = logging.getLogger('periscope.unittests')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger('guessit').setLevel(logging.INFO)


GREEN_FONT = "\x1B[0;32m"
YELLOW_FONT = "\x1B[0;33m"
BLUE_FONT = "\x1B[0;34m"
RED_FONT = "\x1B[0;31m"
RESET_FONT = "\x1B[0m"

def setupLogging(colored = True):
    """Sets up a nice colored logger as the main application logger (not only smewt itself)."""

    class SimpleFormatter(logging.Formatter):
        def __init__(self):
            self.fmt = '%(levelname)-8s %(module)s:%(funcName)s -- %(message)s'
            logging.Formatter.__init__(self, self.fmt)

    class ColoredFormatter(logging.Formatter):
        def __init__(self):
            self.fmt = '%(levelname)-8s ' + BLUE_FONT + '%(mname)-8s %(mmodule)s:%(funcName)s' + RESET_FONT + ' -- %(message)s'
            logging.Formatter.__init__(self, self.fmt)

        def format(self, record):
            modpath = record.name.split('.')
            record.mname = modpath[0]
            record.mmodule = '.'.join(modpath[1:])
            result = logging.Formatter.format(self, record)
            if record.levelno == logging.DEBUG:
                return BLUE_FONT + result
            elif record.levelno == logging.INFO:
                return GREEN_FONT + result
            elif record.levelno == logging.WARNING:
                return YELLOW_FONT + result
            else:
                return RED_FONT + result

    ch = logging.StreamHandler()
    if colored and sys.platform != 'win32':
        ch.setFormatter(ColoredFormatter())
    else:
        ch.setFormatter(SimpleFormatter())
    logging.getLogger().addHandler(ch)


def allTests(testClass):
    return TestLoader().loadTestsFromTestCase(testClass)

def datafile(filename):
    return os.path.join(os.path.split(__file__)[0], 'testdata', filename)

PLUGINS = [ 'Addic7ed', 'Podnapisi', 'TheSubDB', 'OpenSubtitles', 'TvSubtitles' ]
WORKING_PLUGINS_EPISODES = [ 'TvSubtitles', 'Addic7ed', 'OpenSubtitles' ]
WORKING_PLUGINS_MOVIES = [ 'OpenSubtitles', 'Podnapisi' ]

EPISODE_TESTS = [
    { 'video': 'Big.Bang.Theory,.The.2x12.The.Killer.Robot.Instability.HDTV.XviD-XOR.avi',
      'language': 'fr',
      'result': 'The Big Bang Theory - 2x12 - The Killer Robot Instability.HDTV.xor.fr.srt',
      'plugins': WORKING_PLUGINS_EPISODES
      },

    { 'video': 'The.Mentalist.3x18.The.Red.Mile.HDTV.XviD-FEVER.avi',
      'language': 'en',
      'result': 'The.Mentalist.3x18.The.Red.Mile.HDTV.XviD-FEVER.English.srt',
      'plugins': WORKING_PLUGINS_EPISODES
      }

    ]

MOVIE_TESTS = [
    { 'video': 'How.To.Train.Your.Dragon.2010.DVDRip.XviD-TASTE.avi',
      'language': 'en',
      'result': 'subs.english.dragon-taste.srt',
      'plugins': WORKING_PLUGINS_MOVIES
      }
    ]

class TestSubtitles(TestCase):

    def testEpisodeSubs(self):
        self.runTests(EPISODE_TESTS)

    def testMovieSubs(self):
        self.runTests(MOVIE_TESTS)

    def runTests(self, tests):
        total = {}
        correct = {}

        for subdata in tests:
            video = datafile(subdata['video'])
            lang =  subdata['language']
            subfile = subdata['result']
            plugins = subdata['plugins']

            for plugin in plugins:
                total[plugin] = total.get(plugin, 0) + 1
                log.debug('Searching for sub for: ' + video + ' with plugin ' + plugin)
                subdl = periscope.Periscope()
                subdl.pluginNames = [ plugin ]

                subs = subdl.listSubtitles(video, [ lang ])
                if not subs:
                    log.warning('Could not find any sub for: ' + video + ' with plugin ' + plugin)
                    continue

                for sub in subs:
                    log.debug("Found a sub from %s in language %s, downloadable from %s" % (sub['plugin'], sub['lang'], sub['link']))

                sub = subdl.attemptDownloadSubtitleText(subs, [ lang ])

                if sub:
                    result = sub["subtitletext"]
                else:
                    log.warning('Could not complete download for sub for: ' + video + ' with plugin ' + plugin)
                    continue

                #self.assert_(self.subtitlesEqual(result, open(datafile(subfile)).read()))
                if self.subtitlesEqual(result, open(datafile(subfile)).read()):
                    correct[plugin] = correct.get(plugin, 0) + 1

        print '---- Summary ----'
        for plugin, ntests in total.items():
            print 'Plugin %s found %d subs out of %d' % (plugin, correct.get(plugin, 0), ntests)






    def canonicalForm(self, encodedText):
        "Return the subtitle content as a lower-case unicode string with unix EOLs."

        result = encodedText.lower().replace('\r\n', '\n')
        encoding = chardet.detect(result)['encoding']

        # small hack as it seems chardet is not perfect :-)
        if encoding.lower().startswith('iso-8859'):
            encoding = 'iso-8859-1'

        return result.decode(encoding)

    def subtitlesEqual(self, sub1, sub2):
        "Return whether 2 subtitles are equal, allowing for a little bit of differences."

        sub1 = self.canonicalForm(sub1)
        sub2 = self.canonicalForm(sub2)

        # why doesn't this work?
        #        import tempfile
        #        subfile1 = tempfile.NamedTemporaryFile()
        #        subfile1.write(sub1)
        #        subfile1.close()
        #        subfile2 = tempfile.NamedTemporaryFile()
        #        subfile2.write(sub2)
        #        subfile2.close()
        #
        #        # for python >= 2.7
        #        #subprocess.check_output
        #
        #        import subprocess
        #        subprocess.Popen([ 'diff', subfile1.name, subfile2.name ], stdout = subprocess.PIPE)

        subfile1 = '/tmp/sub1.srt'
        subfile2 = '/tmp/sub2.srt'

        open(subfile1, 'w').write(sub1.encode('utf-8'))
        open(subfile2, 'w').write(sub2.encode('utf-8'))
        import subprocess
        diffp = subprocess.Popen([ 'diff', subfile1, subfile2 ], stdout = subprocess.PIPE)
        diff, _ = diffp.communicate()

        os.remove(subfile1)
        os.remove(subfile2)

        # keep only the lines that are actual diff, not part of `diff` syntax
        realdiff = filter(lambda l: l and (l[0] == '<' or l[0] == '>'), diff.split('\n'))

        # remove those diffs that correspond to different indices of the sentences
        realdiff = filter(lambda l: len(l) > 6, realdiff)

        log.debug('Real diff: %s', '\n' + '\n'.join(realdiff))

        # 50 = completely arbitrary ;-)
        if len(realdiff) > 50:
            return False

        return True

suite = allTests(TestSubtitles)


if __name__ == '__main__':
    setupLogging()
    TextTestRunner(verbosity=2).run(suite)
