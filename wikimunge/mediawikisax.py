import bz2
import xml.sax


class MediaWikiSAX(xml.sax.ContentHandler):
  def __init__(self):
    self.depth = 0
    self.content = None
    self.page = None
    self.inNS = False
    self.namespaces = {}


  def parse(self, path, handler):
    self.handler = handler

    parser = xml.sax.make_parser()
    parser.setContentHandler(self)

    def _open(path):
      return bz2.open(path) if path.endswith('.bz2') else open(path, 'r')

    with _open(path) as f: parser.parse(f)


  def expect_tag(self, name, expected):
    if name != expected: raise Exception('Expected <%s> tag' % expected)


  def capture_content(self): self.content = []


  def get_content(self):
    return ''.join(self.content) if self.content is not None else None


  def startElement(self, name, attrs):
    if self.depth == 0:
      self.expect_tag(name, 'mediawiki')

    elif self.depth == 2 and name == 'namespaces':
      self.inNS = True

    elif self.depth == 1 and name == 'page':
      self.page = {}

    else:
      if self.inNS and name == 'namespace':
        self.nsKey = attrs['key']
        self.capture_content()

      if self.page is not None:
        if name == 'redirect':
          self.page['redirect'] = attrs['title']

        if name in ('ns', 'title', 'model', 'text'):
          self.capture_content()

    self.depth += 1


  def endElement(self, name):
    self.depth -= 1

    if self.inNS:
      if name == 'namespaces': self.inNS = False
      if name == 'namespace':
        self.namespaces[self.nsKey] = self.get_content()

    if self.page is not None:
      if name == 'page':
        if 'redirect' in self.page:
          self.page['text'] = [self.page['redirect']]
          model = 'redirect'

        else: model = self.page['model']

        self.handler(model, self.page['ns'], self.page['title'],
                     self.page.get('text', []))

        self.page = None

      if name == 'ns':    self.page['ns'] = self.namespaces[self.get_content()]
      if name == 'title': self.page['title']  = self.get_content()
      if name == 'model': self.page['model']  = self.get_content()
      if name == 'text':  self.page['text']   = self.content

    self.content = None


  def characters(self, data):
    if self.content is not None:
      self.content.append(data)
