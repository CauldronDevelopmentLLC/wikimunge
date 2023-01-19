#!/usr/bin/env python3
#
# Copyright (c) 2023 Cauldron Development LLC.

import re
from setuptools import setup


with open('README.md', 'r') as f:
  long_description = f.read()

description = '''
  Parser and expander for Wikipedia, Wiktionary etc. dump files, with Lua
  execution support.
'''

lualib = 'lua/mediawiki-extensions-Scribunto/includes/engines/LuaCommon/lualib'

setup(
  name = 'wikimunge',
  version = '0.0.1',
  description = re.sub(r'\s+', ' ', description).strip(),
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  author = 'Joseph Coffland',
  author_email = 'joseph@cauldrondevelopment.com',
  url = 'https://github.com/cauldrondevelopmentllc/wikimunge',
  license = 'GPL3+ (some included files have other free licences)',
  download_url = 'https://github.com/cauldrondevelopmentllc/wikimunge',
  scripts = [],
  packages = ['wikimunge'],
  package_data = {
    'wikimunge': [
      'lua/*.lua',
      'lua/mediawiki-extensions-Scribunto/COPYING',
      lualib + '/*.lua',
      lualib + '/ustring/*.lua',
      lualib + '/luabit/*.lua',
      'data/*/*'
    ]
  },
  install_requires = ['lupa', 'dateparser'],
  keywords = ['dictionary', 'wiktionary', 'wikipedia', 'data extraction',
    'wikitext', 'scribunto', 'lua'],
  classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: GPL3+ License',
    'Natural Language :: English',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3 :: Only',
    'Topic :: Text Processing',
    'Topic :: Text Processing :: Linguistic',
  ])
