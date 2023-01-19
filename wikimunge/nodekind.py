import enum


@enum.unique
class NodeKind(enum.Enum):
  '''Node types in the parse tree.'''

  # Root node of the tree.  This represents the parsed document.
  # Its arguments are [pagetitle].
  ROOT = enum.auto(),

  # Level2 subtitle.  Arguments are the title, children are what the section
  # contains.
  LEVEL2 = enum.auto(),

  # Level3 subtitle
  LEVEL3 = enum.auto(),

  # Level4 subtitle
  LEVEL4 = enum.auto(),

  # Level5 subtitle
  LEVEL5 = enum.auto(),

  # Level6 subtitle
  LEVEL6 = enum.auto(),

  # Content to be rendered in italic.  Content is in children.
  ITALIC = enum.auto(),

  # Content to be rendered in bold.  Content is in children.
  BOLD = enum.auto(),

  # Horizontal line.  No arguments or children.
  HLINE = enum.auto(),

  # A list.  Each list will be started with this node, also nested
  # lists.  Args contains the prefix used to open the list.
  # Children will contain LIST_ITEM nodes that belong to this list.
  # For definition lists the prefix ends in ';'.
  LIST = enum.auto(),  # args = prefix for all items of this list

  # A list item.  Nested items will be in children.  Items on the same
  # level will be on the same level.  There is no explicit node for a list.
  # Args is directly the token for this item (not as a list).  Children
  # is what goes in this list item.  List items where the prefix ends in
  # ';' are definition list items.  For them, children contain the item
  # to be defined and node.attrs['def'] contains the definition, which has
  # the same format as children (i.e., a list of strings and WikiNode).
  LIST_ITEM = enum.auto(),  # args = token for this item

  # Preformatted text were markup is interpreted.  Content is in children.
  # Indicated in WikiText by starting lines with a space.
  PREFORMATTED = enum.auto(),  # Preformatted inline text

  # Preformatted text where markup is NOT interpreted.  Content is in
  # children. Indicated in WikiText by <pre>...</pre>.
  PRE = enum.auto(),  # Preformatted text where specials not interpreted

  # An internal Wikimedia link (marked with [[...]]).  The link arguments
  # are in args.  This tag is also used for media inclusion.  Links with
  # trailing word end immediately after the link have the trailing part
  # in link children.
  LINK = enum.auto(),

  # A template call (transclusion).  Template name is in first argument
  # and template arguments in subsequent args.  Children are not used.
  # In WikiText {{name|arg1|...}}.
  TEMPLATE = enum.auto(),

  # A template argument expansion.  Argument name is in first argument and
  # subsequent arguments in remaining arguments.  Children are not used.
  # In WikiText {{{name|...}}}
  TEMPLATE_ARG = enum.auto(),

  # A parser function invocation.  This is also used for built-in
  # variables such as {{PAGENAME}}.  Parser function name is in
  # first argument and subsequent arguments are its parameters.
  # Children are not used.  In WikiText {{name:arg1|arg2|...}}.
  PARSER_FN = enum.auto(),

  # An external URL.  The first argument is the URL.  The second optional
  # argument is the display text. Children are not used.
  URL = enum.auto(),

  # A table.  Content is in children.
  TABLE = enum.auto(),

  # A table caption (under TABLE).  Content is in children.
  TABLE_CAPTION = enum.auto(),

  # A table row (under TABLE).  Content is in children.
  TABLE_ROW = enum.auto(),

  # A table header cell (under TABLE_ROW).  Content is in children.
  # Rows where all cells are header cells are header rows.
  TABLE_HEADER_CELL = enum.auto(),

  # A table cell (under TABLE_ROW).  Content is in children.
  TABLE_CELL = enum.auto(),

  # A MediaWiki magic word.  The magic word is assigned directly to args
  # (not as a list).  Children are not used.
  MAGIC_WORD = enum.auto(),

  # HTML tag (open or close tag).  Pairs of open and close tags are
  # merged into a single node and the content between them is stored
  # in the node's children.  Args is the name of the tag directly
  # (i.e., not a list and always without a slash).  Attrs contains
  # attributes from the HTML start tag.  Contents in a paired tag
  # are stored in ``children``.
  HTML = enum.auto(),
