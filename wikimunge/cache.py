import os
import re
import pickle


def __get_template_body(text):
  def text_at(i): return text[i] if i < len(text) else ''
  def is_tag_char(c): return 'a' <= c and c <= 'z'

  def match_space(i):
    while text_at(i).isspace(): i += 1
    return i

  def match_tag_name(i):
    while is_tag_char(text_at(i)): i += 1
    return i

  def match_tag(i):
    if text_at(i) != '<': return
    i = match_space(i + 1)

    end_tag = text_at(i) == '/'
    if end_tag: i = match_space(i + 1)

    start = i
    end = match_tag_name(i)
    if end == start: return
    i = match_space(end)

    closed_tag = text_at(i) == '/' and not end
    if closed_tag: i = match_space(i + 1)

    if text_at(i) == '>':
      return i + 1, text[start : end], end_tag, closed_tag

  def start_comment(i):
    if text_at(i) == '<' and text_at(i + 1) == '!':
      i = match_space(i + 2)
      if text_at(i) == '-' and text_at(i + 1) == '-':
        return i + 2

  def end_comment(i):
    if text_at(i) == '-' and text_at(i + 1) == '-':
      i = match_space(i + 2)
      return i + 1 if text_at(i) == '>' else None


  parts = []
  stack = []
  i = 0

  while i < len(text):
    tag  = match_tag(i)
    scom = start_comment(i)
    ecom = end_comment(i)

    if tag:
      tag_end, tag_name, end_tag, closed_tag = tag

      if tag_name in ('noinclude', 'includeonly', 'onlyinclude'):
        if end_tag and len(stack) and stack[-1] == tag_name: stack.pop()
        if not end_tag and not closed_tag: stack.append(tag_name)
        i = tag_end

    elif scom:
      stack.append('comment')
      i = scom

    elif ecom and len(stack) and stack[-1] == 'comment':
      stack.pop()
      i = ecom

    else:
      if not len(stack) or stack[-1] == 'includeonly': parts.append(text_at(i))
      i += 1

  return ''.join(parts)


def _get_template_body(text):
  '''Extracts the portion to be transcluded from a template body.'''
  assert isinstance(text, str)

  # Remove all comments
  text = re.sub(r'(?s)<!\s*--.*?--\s*>', '', text)

  # Remove all text inside <noinclude> ... </noinclude>
  text = re.sub(r'(?is)<\s*noinclude\s*>.*?<\s*/\s*noinclude\s*>', '', text)

  # Handle <noinclude> without matching </noinclude> by removing the
  # rest of the file.  <noinclude/> is handled specially elsewhere, as
  # it appears to be used as a kludge to prevent normal interpretation
  # of e.g. [[ ... ]] by placing it between the brackets.
  text = re.sub(r'(?is)<\s*noinclude\s*>.*', '', text)

  # Apparently unclosed <!-- at the end of a template body is ignored
  text = re.sub(r'(?s)<!\s*--.*', '', text)

  # <onlyinclude> tags, if present, include the only text that will be
  # transcluded.  All other text is ignored.
  onlys = list(
    re.finditer(r'(?is)<\s*onlyinclude\s*>(.*?)<\s*/\s*onlyinclude\s*>|'
                r'<\s*onlyinclude\s*/\s*>', text))
  if onlys: text = ''.join(m.group(1) or '' for m in onlys)

  # Remove <includeonly>.  They mark text that is not visible on the page
  # itself but is included in transclusion.  Also text outside these tags
  # is included in transclusion.
  return re.sub(r'(?is)<\s*(/\s*)?includeonly\s*(/\s*)?>', '', text)


class PageCache:
  def __init__(self, name_data, path):
    self.name_data    = name_data
    self.path         = path

    self.buf          = None
    self.offset       = 0
    self.pages        = {}
    self.redirects    = {}
    self.templates    = {}
    self.rev_redirect = None

    self.load()


  def load(self):
    buf_path  = self.path + '/cache'
    info_path = buf_path + '.pickle'

    if os.path.exists(buf_path) and os.path.exists(info_path):
      with open(info_path, 'rb') as f: data = pickle.load(f)
      self.pages, self.redirects, self.templates = data

    self.buf = open(buf_path, 'ab+', buffering = 0)
    self.offset = self.buf.tell()


  def save(self):
    with open(self.path + '/cache.pickle', 'wb') as f:
      pickle.dump((self.pages, self.redirects, self.templates), f)


  def has_template(self, title):
    title = self.name_data.canonicalize_template_name(title)


  def add_template(self, title, text):
    name = self.name_data.canonicalize_template_name(title)
    self.templates[name] = _get_template_body(text)


  def set_template(self, title, text):
    if self.rev_redirect is None:
      self.rev_redirect = {}

      for k, v in self.redirects.items():
        if not v in self.rev_redirect: self.rev_redirect[v] = []
        self.rev_redirect[v].append(k)

    self.add_template(title, text)

    for redir in self.rev_redirect.get(title, []):
      self.set_template(redir, text)


  def redirect_templates(self):
    prefix = self.name_data.get_name('Template') + ':'

    for k, v in self.redirects.items():
      if not (k.startswith(prefix) and v.startswith(prefix)): continue

      k = self.name_data.canonicalize_template_name(k)
      v = self.name_data.canonicalize_template_name(v)

      if k in self.templates or v not in self.templates: continue

      self.templates[k] = self.templates[v]


  def exists(self, title):
    '''Returns True if the given page exists'''
    assert isinstance(title, str)

    if title.startswith('Main:'): title = title[5:]
    if title in self.pages: return True

    # Try with local module prefix
    prefix = self.name_data.get_name('Module') + ':'
    if title.startswith('Module:'):
      return prefix + title[7:] in self.pages

    return False


  def add(self, model, title, text):
    assert isinstance(model, str)
    assert isinstance(title, str)
    assert isinstance(text,  str)

    # Save page
    raw = text.encode('utf-8')
    os.pwrite(self.buf.fileno(), raw, self.offset)
    self.pages[title] = (model, self.offset, len(raw))
    self.offset += len(raw)

    if model == 'redirect': self.redirects[title] = text

    elif title.startswith(self.name_data.get_name('Template') + ':'):
      # XXX These are insufficient for other languages
      if title.endswith('/documentation') or title.endswith('/testcases'):
        return

      self.add_template(title, text)


  def read(self, title):
    '''Reads page contents. Returns None if the page does not exist.'''
    assert isinstance(title, str)

    if title.startswith('Main:'): title = title[5:]

    if title in self.pages:
      model, offset, size = self.pages[title]
      return os.pread(self.buf.fileno(), size, offset).decode('utf-8')
