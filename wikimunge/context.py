import sys

from .cache     import PageCache
from .wikinode  import NodeKind
from .common    import MAGIC_FIRST, MAX_MAGICS
from .encoder   import encode
from .expander  import expand
from .parser    import parse


class Context(object):
  def __init__(self, name_data, cache, template_filter = None, log = None):
    self.name_data         = name_data
    self.cache             = cache
    self.template_filter   = template_filter
    self.log               = log
    self.title             = None
    self.LANGUAGES_BY_CODE = {} # XXX Some templates need this
    self.lua               = None
    self.lua_depth         = 0
    self.lua_invoke        = None
    self.lua_reset_env     = None


  def message(self, kind, msg, trace):
    if self.expand_stack: msg += ' at {}'.format(self.expand_stack)

    if self.parser_stack:
      titles = []

      for node in self.parser_stack:
        if node.kind in (NodeKind.LEVEL2, NodeKind.LEVEL3, NodeKind.LEVEL4,
                         NodeKind.LEVEL5, NodeKind.LEVEL6):
          if not node.args: continue
          lst = [x if isinstance(x, str) else '???' for x in node.args[0]]
          title = ''.join(lst)
          titles.append(title.strip())
          msg += ' parsing ' + '/'.join(titles)

    if trace: msg += '\n' + trace

    msg = '%s: %s: %s' % (self.title, kind, msg)

    if self.log:
      self.log.write(msg + '\n')
      self.log.flush()

    if kind != 'DEBUG':
      sys.stderr.write(msg + '\n')
      sys.stderr.flush()


  def error(  self, msg, trace = None): self.message('ERROR',   msg, trace)
  def warning(self, msg, trace = None): self.message('WARNING', msg, trace)
  def debug(  self, msg, trace = None): self.message('DEBUG',   msg, trace)


  def has_cookie(self,  idx): return 0 <= idx and idx < len(self.cookies)
  def load_cookie(self, idx): return self.cookies[idx]


  def save_cookie(self, kind, args, nowiki):
    '''Saves a value and returns a unique magic cookie for it.'''
    assert kind in (
      'T',  # Template {{ ... }}
      'A',  # Template argument {{{ ... }}}
      'L',  # link
      'E',  # external link
      'N',  # nowiki text
    )
    assert isinstance(args, (list, tuple))
    assert nowiki in (True, False)

    v = (kind, tuple(args), nowiki)

    if v in self.rev_ht: return self.rev_ht[v]
    idx = len(self.cookies)

    if MAX_MAGICS <= idx:
      self.error('too many templates, arguments, or parser function calls')
      return ''

    self.cookies.append(v)

    ch = self.rev_ht[v] = chr(MAGIC_FIRST + idx)
    return ch


  def expand_template(self, title):
    if self.template_filter:
      title = self.name_data.canonicalize_template_name(title)
      return self.template_filter(title)

    return True


  def get_template(self, title):
    title = self.name_data.canonicalize_template_name(title)
    return self.cache.templates.get(title)


  def encode(self, text): return encode(self, text)
  def parse(self, text): return parse(self, text)


  def expand(self, text, parent = None, timeout = None):
    return expand(self, text, parent)


  def page_redirect(self, title): return self.cache.redirects.get(title)
  def page_exists(  self, title): return self.cache.exists(title)
  def read_by_title(self, title): return self.cache.read(title)


  def start_page(self, title):
    self.title                 = title

    # Magic cookies
    self.cookies               = []
    self.rev_ht                = {}

    # Expand
    self.expand_stack          = [title]

    # Parse
    self.parser_stack          = []
    self.linenum               = None
    self.pre_parse             = False
    self.suppress_special      = None
    self.beginning_of_line     = None
    self.wsp_beginning_of_line = None
