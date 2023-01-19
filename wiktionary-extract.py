#!/usr/bin/env python3

import os
import json
import re
import html
import argparse

from wikimunge import WikiMunge, WikiNode, NodeKind

json_args = dict(ensure_ascii = False, indent = 2, separators = (',', ': '))
chars = '0123456789aáâåäbcdeéfghijklmnoóöõpqrsšștuüvwxyzž '


configs = {
  'fi': {
    'lang':                'Suomi',
    'lang_code':           'fi',
    'upload_url':          'https://upload.wikimedia.org/wiktionary/fi',
    'keywords': {
      'Wiktionary': 'Wikisanakirja',
      'Template':   'Malline',
      'Module':     'Moduuli',
      'Image':      'Kuva',
      'File':       'Tiedosto',
      'Appendix':   'Liite',
      'Category':   'Luokka',
      'thumbnail':  'pienoiskuva',
    },

    'pos': {
      'substantiivi':     'noun',
      'verbi':            'verb',
      'adjektiivi':       'adjective',
      'lyhenne':          'abbrev',
      'adverbi':          'adverb',
      'suffiksi':         'suffix',
      'prefiksi':         'prefix',
      'interjektio':      'interjection',
      'pronomini':        'pronoun',
      'numeraali':        'number',
      'konjunktio':       'conjunction',
      'postpositio':      'postposition',
      'partikkeli':       'particle',
      'supistuma':        'contraction',
      'prepositio':       'preposition',
      'infiksi':          'infix',
      # 'erisnimi':       'name',
      # 'aakkonen':       'letter',
      # 'fraasi':         'phrase',
      # 'symboli':        'symbol',
    },
    'section': {
      'etymologia':       'etymology',
      'ääntäminen':       'sounds',
      'käännökset':       'translations',
      'liittyvät sanat':  'related',
   },
    'related': {
      'yläkäsitteet':     'hypernyms',
      'vieruskäsitteet':  'cohyponyms',
      'yhdyssanat':       'compounds',
      'synonyymit':       'synonyms',
      'johdokset':        'derived',
      'alakäsitteet':     'hyponyms',
      'vastakohdat':      'antonyms',
      'tavutus':          'hyphenations',
      'rinnakkaismuodot': 'alt_of',
      'yhdyssanat ja sanaliitot': 'compounds',
      'osakäsitteet':     'meronym',
      'vastakohta':       'antonyms',
      'lähikäsitteet':    'related',
      'lyhenteet':        'abreviations',
    }
  },
  'en': {
    'lang':              'Finnish',
    'lang_code':         'en',
    'keywords': {},

    'pos': {
      'noun':            'noun',
      'verb':            'verb',
      'adjective':       'adjective',
      'abbrev':          'abbrev',
      'adverb':          'adverb',
      'suffix':          'suffix',
      'prefix':          'prefix',
      'interjetion':     'interjection',
      'pronoun':         'pronoun',
      'number':          'number',
      'conjunction':     'conjunction',
      'postposition':    'postposition',
      'particle':        'particle',
      'contraction':     'contraction',
      'postposition':    'preposition',
      'infix':           'infix',
    },
    'section': {
      'etymology':        'etymology',
      'pronunciation':    'sounds',
      'translations':     'translations',
    },
    'related': {
      'hypernyms':        'hypernyms',
      'cohyponyms':       'cohyponyms',
      'compounds':        'compounds',
      'synonyms':         'synonyms',
      'derived':          'derived',
      'hyponyms':         'hyponyms',
      'antonyms':         'antonyms',
      'hyphenations':     'hyphenations',
      'alt_of':           'alt_of',
      'compounds':        'compounds',
      'meronym':          'meronym',
      'related':          'related',
      'abreviations':     'abreviations',
    }
  }
}


all_words = set()


def title_to_filename(title):
  title = ''.join([c for c in title.strip() if c in chars])
  return title.replace(' ', '_')


def match_node(node, kind, arg0 = None):
  if not isinstance(kind, (list, tuple)): kind = [kind]

  return (isinstance(node, WikiNode) and node.kind in kind and
          (arg0 is None or node.args[0][0] == arg0))


def filter_node(node):
  if isinstance(node, list):
    results = []

    for item in node:
      result = filter_node(item)
      if isinstance(result, list): results += result
      else: results.append(result)

    return results

  if match_node(node, NodeKind.HLINE): return ''

  if match_node(node, NodeKind.HTML) and node.args in ('span', 'nowiki'):
    return filter_node(node.children)

  if match_node(node, NodeKind.LINK):
    for i in range(len(node.args)):
      node.args[i] = [WikiNode.to_text(filter_node(node.args[i]))]

    node.args[0][0] = re.sub(r'#.*$', '', node.args[0][0])

    # Filter out Wiki links
    if ':' in node.args[0][0]:
      if len(node.args) == 1: return ''
      else: return node.args[-1]

    elif node.args[0][0] in all_words: return node
    else: return node.args[-1][0]

  if match_node(node, NodeKind.HTML):
    node.attrs = {k: v for k, v in node.attrs.items()
                  if k not in ('class', 'lang')}

  if isinstance(node, WikiNode):
    node.children = filter_node(node.children)
    return node

  return node


def node_to_text(node):
  text = WikiNode.to_text(filter_node(node))
  return html.unescape(text).strip()


def extract_example(node, word):
  children = []
  trans = []

  for child in node.children:
    if match_node(child, NodeKind.LIST):
      for item in child.children:
        t = node_to_text(item.children)
        if t: trans.append(t)

    else: children.append(child)

  text = node_to_text(children).replace('~', word)
  if text:
    d = dict(text = text)

    if len(trans):
      trans = node_to_text(trans)
      if trans: d['trans'] = trans

    return d


def extract_examples(node, word):
  exs = []

  for child in node.children:
    if match_node(child, NodeKind.LIST_ITEM):
      ex = extract_example(child, word)
      if ex: exs.append(ex)

  return exs if exs else None


def extract_sense(node, word):
  # Extract examples
  exs = None
  for i in range(len(node.children)):
    child = node.children[i]
    if match_node(child, NodeKind.LIST):
      exs = extract_examples(child, word)
      del node.children[i]
      break

  # Extract sense
  text = node_to_text(node.children)

  if text or exs:
    sense = dict()
    if text: sense['glosses'] = [text]
    if exs:  sense['examples'] = exs
    return sense


def extract_sound(node):
  text = node_to_text(node)
  if not text.startswith('Rhymes:'):
    return text


def extract_sounds(node):
  sounds = []

  for child in node.children:
    if match_node(child, NodeKind.LIST):
      sounds += extract_sounds(child)

    elif match_node(child, NodeKind.LIST_ITEM):
      sounds.append(extract_sound(child.children))

    elif isinstance(child, WikiNode):
      sounds.append(extract_sound(child))

  return [sound for sound in sounds if sound]


def extract_etymology(node):
  return node_to_text(node.children)


def extract_related_list(node):
  items = []

  for child in node.children:
    if match_node(child, NodeKind.LIST_ITEM):
      text = node_to_text(child.children)
      items += [x.strip() for x in text.split(',') if x.strip()]

  return items


def extract_related_nav_frame(node):
  items = []

  for child in node.children:
    if (match_node(child, NodeKind.HTML) and
        'NavContent' in child.attrs.get('class', '')):
      for e in child.children:
        if match_node(e, NodeKind.LIST):
          items += extract_related_list(e)

  return items


def extract_to_related(node, related, category):
  items = related.get(category, [])

  for child in node.children:
    if (match_node(child, NodeKind.HTML) and
        child.attrs.get('class') == 'NavFrame'):
      items += extract_related_nav_frame(child)

    elif match_node(child, NodeKind.LIST):
      items += extract_related_list(child)

    elif isinstance(child, str):
      text  = node_to_text(child)
      items += [x.strip() for x in text.split(',') if x.strip()]

  if len(items): related[category] = sorted(set(items))


def extract_related(node):
  related = {}

  for child in node.children:
    if match_node(child, NodeKind.LIST):
      if not 'related' in related: related['related'] = []
      related['related'] += extract_related_list(child)

    if match_node(child, NodeKind.LEVEL5):
      title = child.args[0][0].lower()
      if title in config['related']:
        category = config['related'][title]
        extract_to_related(child, related, category)

  return related


def extract_translations(node):
  if not isinstance(node, WikiNode): return []

  t = []
  if 1 < len(node.children):
    first = node.children[0]
    if isinstance(first, str) and first == 'englanti: ':
      t = [n.strip() for n in node_to_text(node.children[1:]).split(',')]

  if not t:
    for child in node.children: t += extract_translations(child)

  return sorted(list(set(t)))


def extract_section(node, section):
  if section == 'sounds':       return extract_sounds(node)
  if section == 'etymology':    return extract_etymology(node)
  if section == 'translations': return extract_translations(node)
  if section == 'related':      return extract_related(node)


def extract_senses(node, word):
  senses = []

  for child in node.children:
    if match_node(child, NodeKind.LIST):
      for item in child.children:
        if match_node(item, NodeKind.LIST_ITEM):
          sense = extract_sense(item, word)
          if sense: senses.append(sense)

  return senses


_levels = (NodeKind.LEVEL2, NodeKind.LEVEL3, NodeKind.LEVEL4, NodeKind.LEVEL5,
           NodeKind.LEVEL6)

def extract_levels(node):
  for child in node.children:
    if match_node(child, _levels):
      yield child
      yield from extract_levels(child)


def extract_defs(node, word, lang):
  defs = []
  first_pos = True
  d = dict(word = word, lang = lang)

  #print('%r' % node)

  for child in extract_levels(node):
    if child.kind != NodeKind.LEVEL2:
      title = ''.join(child.args[0]).split()[0].lower()

      # POS
      if title in config['pos']:
        pos = config['pos'][title]
        senses = extract_senses(child, word)

        if first_pos:
          first_pos = False
          d |= dict(pos = pos, senses = senses)

        else: d = dict(word = title, lang = lang, pos = pos, senses = senses)

        defs.append(d)

      # Sections
      if title in config['section']:
        section = config['section'][title]
        d[section] = extract_section(child, section)

      # Related
      if title in config['related']:
        category = config['related'][title]
        if not 'related' in d: d['related'] = {}
        extract_to_related(child, d['related'], category)

  return dict(word = word, defs = defs)


def sanitize_text(text):
  text = text.replace('\r', '')
  text = re.sub(r'(?s)<strong class="error">.*</strong>', '', text)
  text = re.sub(r'\[\[\s*Category:[^\]<>]*\]\]', '', text)
  text = re.sub(r'data-[\w-]+="[^"]*"', '', text) # Parsing problems
  text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text) # char refs
  return text


class WiktionaryExtractor:
  def __init__(self, config, outdir, threads, log = None, expand_only = False,
               match_title = None, max_pages = None):
    self.config = config
    self.outdir = outdir
    self.expand_only = expand_only
    self.match_title = re.compile(match_title) if match_title else None
    self.max_pages = max_pages

    for name in ('dict', 'expanded'):
      path = '%s/%s' % (outdir, name)
      if not os.path.exists(path): os.makedirs(path)

    self.load_titles()

    tfilt = lambda title: not re.match(r'^fi-((decl)|(conj))', title)

    self.munge = WikiMunge(
      config['lang_code'], outdir, template_filter = tfilt, log = log,
      threads = threads)


  def load_titles(self):
    path = self.outdir + '/titles.txt'

    if not os.path.exists(path): self.titles = []
    else:
      with open(path, 'r') as f:
        self.titles = [line.strip() for line in f]


  def save_titles(self):
    path = self.outdir + '/titles.txt'

    if len(self.titles):
      with open(path, 'w') as f:
        for title in self.titles:
          f.write(title + '\n')


  def get_ns(self, ns): return self.config['namespaces'].get(ns, ns)


  def save_dict_entry(self, path, data):
    if os.path.exists(path):
      with open(path, 'r') as f:
        d = json.load(f)
        d['defs'] += data['defs']
        data = d

    with open(path, 'w') as f:
      json.dump(data, f, **json_args)


  def extract_page(self, title, text):
    if self.match_title and not self.match_title.match(title): return

    filename = title.replace(' ', '_').replace('/', '_')
    exp_path = self.outdir + '/expanded/%s.txt' % filename

    if os.path.exists(exp_path) and not self.expand_only:
      with open(exp_path, 'r') as f: text = f.read()
    else:
      text = self.munge.expand(title, text)
      with open(exp_path, 'w') as f: f.write(text)

    if self.expand_only: return

    text = sanitize_text(text)
    tree = self.munge.parse(title, text)
    data = extract_defs(tree, title, config['lang'])

    if data: return title, data


  def page_handler(self, model, ns, title, text):
    if model == 'redirect' or (
        ns and ns != 'Talk' and not ns.endswith(' talk')):
      self.munge.add_page(model, title, ''.join(text))

    elif model == 'wikitext':
      tag = '==%s==' % self.config['lang']
      text = ''.join(text)
      i = text.find(tag)

      if i != -1 and (i == 0 or text[i - 1] in '\r\n'):
        text = text[i:]
        i = 0

        while i != -1:
          i = text.find('==', i + 1)
          if i != -1 and text[i - 1] in '\r\n' and text[i + 2] != '=':
            text = text[0 : i]
            i = -1

        self.titles.append(title)
        self.munge.add_page(model, title, text)


  def run(self, path):
    global all_words

    # Load pages
    if not self.munge.cache.offset:
      self.titles = []
      self.munge.process(path, self.page_handler)
      self.save_titles()

    # Disable known bad templates
    for name in ('slim-wikipedia', 'wikipedia', 'pedia', 'number box',
                 'specieslite'):
      self.munge.cache.set_template('Template:' + name, '')

    # Map titles
    all_words = set(self.titles)

    # Extract entries
    titles = self.titles[0 : self.max_pages]
    results = self.munge.reprocess(titles, self.extract_page)

    # Save extracted data
    for title, data in results:
      filename = title_to_filename(title)
      path = self.outdir + '/dict/%s.json' % filename
      self.save_dict_entry(path, data)


parser = argparse.ArgumentParser(
  prog = 'wiktionary-extract',
  description = 'Extract language data from wiktionary dump files.')
parser.add_argument('filename', help = 'Wiktionary XML input file')
parser.add_argument('-l', '--lang', help = 'Input file language',
                    required = True, choices = configs.keys())
parser.add_argument('--expand-only', help = 'Only expand entries',
                    action = 'store_true')
parser.add_argument('-m', '--match', metavar = 'REGEX',
                    help = 'Only process entries with matching titles.')
parser.add_argument('--threads', type = int,
                    help = 'Number of processor threads to use.')
parser.add_argument('-n', '--max-pages', type = int,
                    help = 'Maximum number of pages to expand.')

args = parser.parse_args()
config = configs[args.lang]

outdir = 'output/' + args.lang
log = outdir + '/log.txt'

we = WiktionaryExtractor(
  config, outdir, threads = args.threads, log = log,
  match_title = args.match, expand_only = args.expand_only,
  max_pages = args.max_pages)

we.run(args.filename)
