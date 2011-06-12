from setuptools import setup
from periscope import version

PACKAGE = 'periscope-ng'

setup(name = PACKAGE, version = version.VERSION,
      license = "GNU LGPL",
      description = "Python module to search and download subtitles",
      author = "Antoine Bertin",
      author_email = "diaoulael@gmail.com",
      url = "https://github.com/Diaoul/periscope-ng",
      packages= ["periscope", "periscope/plugins"],
      py_modules=["periscope"],
      scripts = ["bin/periscope"],
      install_requires = ["BeautifulSoup == 3.2.0", "guessit == 0.2"]
      )
