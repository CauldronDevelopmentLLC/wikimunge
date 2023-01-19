import re
import json

from .namespace import Namespace
from .parserfns import PARSER_FUNCTIONS


class NamespaceData:
  def __init__(self, path):
    with open(path, encoding = 'utf-8') as f:
      self.data = json.load(f)

    # See lua/mw_site.lua
    self.namespaces = {}

    for ns_can_name, ns_data in self.data.items():
      self.namespaces[ns_data['id']] = Namespace(
        id            = ns_data['id'],
        name          = ns_data['name'],
        isSubject     = ns_data['issubject'],
        isContent     = ns_data['content'],
        isTalk        = ns_data['istalk'],
        aliases       = ns_data['aliases'],
        canonicalName = ns_can_name)

    for ns in self.namespaces.values():
      if ns.isContent and 0 <= ns.id: ns.talk = self.namespaces[ns.id + 1]
      elif ns.isTalk: ns.subject = self.namespaces[ns.id - 1]


  def get(self, name):
    i = name.find(':')
    if i != -1: name = name[:i]

    ns = self.data.get(name)
    if ns: return ns

    for ns in self.namespaces.values():
      if ns.match(name): return ns


  def get_name(self, name): return self.get(name)['name']


  def canonicalize_parserfn_name(self, name):
    name = re.sub(r'\s+', ' ', name.replace('_', ' ')).strip()

    # Parser function names are case-insensitive
    if name not in PARSER_FUNCTIONS: name = name.lower()

    return name


  def canonicalize_template_name(self, name):
    tmpl = self.get_name('Template').lower() + ':'
    if name.lower().startswith(tmpl): name = name[len(tmpl):]

    name = name.replace('_', ' ')
    name = name.replace('(', '%28')
    name = name.replace(')', '%29')
    name = name.replace('&', '%26')
    name = name.replace('+', '%2B')
    name = re.sub(r'\s+', ' ', name)

    return name.strip()
