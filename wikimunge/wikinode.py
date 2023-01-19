from .nodekind import NodeKind


kind_to_level = {
  NodeKind.LEVEL2: '==',
  NodeKind.LEVEL3: '===',
  NodeKind.LEVEL4: '====',
  NodeKind.LEVEL5: '=====',
  NodeKind.LEVEL6: '======',
}


def quote_str(s): return str(s).replace('\'', '&apos;').replace('"', '&quot;')
def to_attr(k, v):   return '%s="%s"' % (str(k), quote_str(v)) if v else str(k)
def to_attrs(attrs): return ' '.join([to_attr(k, v) for k, v in attrs.items()])


def to_args(args, sep = '|'):
  return sep.join([WikiNode.to_text(arg) for arg in args])


def to_indented_list(l):
  l = [WikiNode.to_text(x) for x in l]
  return '  ' + '\n  '.join([x.rstrip().replace('\n', '\n  ') for x in l])


class WikiNode:
  '''Node in the parse tree for WikiMedia text.'''

  __slots__ = (
    'kind',
    'args',
    'attrs',
    'children',
    'line',
  )

  def __init__(self, kind, line):
    assert isinstance(kind, NodeKind)
    assert isinstance(line, int)

    self.kind     = kind
    self.args     = []    # List of lists
    self.attrs    = {}
    self.children = []    # List of str and WikiNode
    self.line     = line


  def to_repr(self, depth = 0):
    indent = ' ' * (depth * 2)

    if isinstance(self.args, str): args = self.args
    else: args = ', '.join(map(repr, self.args))

    children = ',\n'.join([
      child.to_repr(depth + 1) if isinstance(child, WikiNode) else
      indent + '  ' + repr(child) for child in self.children])
    if children: children = '\n%s\n%s' % (children, indent)

    return '%s<%s(%s)%s%s>' % (
      indent, self.kind.name, args, self.attrs, children)


  def __repr__(self): return self.to_repr()


  def __str__(self):
    kind = self.kind

    if kind in kind_to_level:
      tag = kind_to_level[kind]
      t = WikiNode.to_text(self.args)
      return '\n%s %s %s\n' % (tag, t, tag) + WikiNode.to_text(self.children)

    if kind == NodeKind.HLINE: return '<hr/>'

    if kind == NodeKind.LIST:
      return '<ol>\n' + to_indented_list(self.children) + '\n</ol>'

    if kind == NodeKind.LIST_ITEM:
      return '<li>' + WikiNode.to_text(self.children) + '</li>'

    if kind == NodeKind.PRE:
      return '<pre>' + WikiNode.to_text(self.children) + '</pre>'

    if kind == NodeKind.PREFORMATTED: return WikiNode.to_text(self.children)
    if kind == NodeKind.LINK:         return '[['  + to_args(self.args) + ']]'
    if kind == NodeKind.TEMPLATE:     return '{{'  + to_args(self.args) + '}}'
    if kind == NodeKind.TEMPLATE_ARG: return '{{{' + to_args(self.args) + '}}}'

    if kind == NodeKind.PARSER_FN:
      prefix = '{{' + WikiNode.to_text(self.args[0]) + ':'
      return prefix + to_args(self.args[1:]) + '}}'

    if kind == NodeKind.URL:
      return '<a href="%s">%s</a>' % (
        WikiNode.to_text(self.args[0]), WikiNode.to_text(self.args[-1]))

    if kind == NodeKind.TABLE:
      return '<table %s>\n%s\n</table>' % (
        to_attrs(self.attrs), to_indented_list(self.children))

    if kind == NodeKind.TABLE_CAPTION:
      return '<caption %s>%s</caption>' % (
        to_attrs(self.attrs), WikiNode.to_text(self.children))

    if kind == NodeKind.TABLE_ROW:
      return '<tr %s>\n%s\n</tr>' % (
        to_attrs(self.attrs), to_indented_list(self.children))

    if kind == NodeKind.TABLE_HEADER_CELL:
      return '<th %s>%s</th>' % (
        to_attrs(self.attrs) if self.attrs else '',
        WikiNode.to_text(self.children))

    if kind == NodeKind.TABLE_CELL:
      return '<td %s>%s</td>' % (
        to_attrs(self.attrs) if self.attrs else '',
        WikiNode.to_text(self.children))

    if kind == NodeKind.HTML:
      parts = ['<%s' % self.args]

      if self.attrs: parts += [' ', to_attrs(self.attrs)]
      if self.children:
        parts += ['>', WikiNode.to_text(self.children), '</%s>' % self.args]

      else: parts.append('/>')

      return ''.join(parts)

    if kind == NodeKind.ROOT: return WikiNode.to_text(self.children)

    if kind == NodeKind.BOLD:
      return '<b>' + WikiNode.to_text(self.children) + '</b>'

    if kind == NodeKind.ITALIC:
      return '<i>' + WikiNode.to_text(self.children) + '</i>'

    raise RuntimeError('Unsupported node %s' % kind)


  @staticmethod
  def to_text(node):
    if isinstance(node, str): return node

    if isinstance(node, (list, tuple)):
      return ''.join([WikiNode.to_text(n) for n in node])

    if not isinstance(node, WikiNode):
      raise RuntimeError('Invalid WikiNode: %s' % node)

    return str(node)
