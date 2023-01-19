import re
import html

from .encoder   import encode
from .parserfns import call_parser_function, PARSER_FUNCTIONS
from .common    import MAGIC_NOWIKI_CHAR, MAGIC_FIRST, MAGIC_LAST
from .luaexec   import call_lua_sandbox


def _unexpanded_template(args, nowiki):
  '''Formats an unexpanded template (whose arguments may have been
    partially or fully expanded).'''
  if nowiki:
    return ('&lbrace;&lbrace;' + '&vert;'.join(args) +
            '&rbrace;&rbrace;')

  return '{{' + '|'.join(args) + '}}'


def _unexpanded_arg(args, nowiki):
  '''Formats an unexpanded template argument reference.'''
  if nowiki:
    return ('&lbrace;&lbrace;&lbrace;' + '&vert;'.join(args) +
            '&rbrace;&rbrace;&rbrace;')
  return '{{{' + '|'.join(args) + '}}}'


def _unexpanded_link(args, nowiki):
  '''Formats an unexpanded link.'''

  if nowiki: return '&lsqb;&lsqb;' + '&vert;'.join(args) + '&rsqb;&rsqb;'
  return '[[' + '|'.join(args) + ']]'


def _unexpanded_extlink(args, nowiki):
  '''Formats an unexpanded external link.'''

  if nowiki: return '&lsqb;' + '&vert;'.join(args) + '&rsqb;'
  return '[' + '|'.join(args) + ']'


def expand(ctx, text, parent = None, timeout = None):
  '''Expands templates and parser functions and Lua macros from ``text``
  (which is from page with title ``title``).'''

  assert isinstance(text, str)
  assert parent is None or (
    isinstance(parent, (list, tuple)) and len(parent) == 2)
  assert ctx.title is not None
  assert timeout is None or isinstance(timeout, (int, float))

  # Handle <nowiki> in a preprocessing step
  text = preprocess_text(ctx, text)


  def invoke_fn(invoke_args, expander, parent):
    '''This is called to expand a #invoke parser function.'''
    assert isinstance(invoke_args, (list, tuple))
    assert callable(expander)
    assert isinstance(parent, (tuple, type(None)))

    # Use the Lua sandbox to execute a Lua macro.  This will initialize
    # the Lua environment if it does not already exist (it needs to be
    # re-created for each page).
    return call_lua_sandbox(ctx, invoke_args, expander, parent, timeout)


  def expand_recur(coded, parent):
    '''This function does most of the work for expanding encoded
    templates, arguments, and parser functions.'''
    assert isinstance(coded, str)
    assert isinstance(parent, (tuple, type(None)))

    def expand_args(coded, argmap):
      assert isinstance(coded, str)
      assert isinstance(argmap, dict)
      parts = []
      pos = 0
      for m in re.finditer(r'[%c-%c]' % (MAGIC_FIRST, MAGIC_LAST), coded):
        new_pos = m.start()

        if pos < new_pos: parts.append(coded[pos:new_pos])
        pos = m.end()
        ch  = m.group(0)
        idx = ord(ch) - MAGIC_FIRST
        kind, args, nowiki = ctx.load_cookie(idx)

        assert isinstance(args, tuple)
        if nowiki:
          # If this template/link/arg has <nowiki />, then just
          # keep it as-is (it won't be expanded)
          parts.append(ch)
          continue

        if kind == 'T':
          # Template transclusion or parser function call.
          # Expand its arguments.
          new_args = tuple([expand_args(x, argmap) for x in args])
          parts.append(ctx.save_cookie(kind, new_args, nowiki))
          continue

        if kind == 'A':
          # Template argument reference
          if 2 < len(args):
            ctx.debug('too many args ({}) in argument reference: {!r}'
                      .format(len(args), args))
          ctx.expand_stack.append('ARG-NAME')
          k = expand_recur(expand_args(args[0], argmap), parent).strip()
          ctx.expand_stack.pop()

          if k.isdigit(): k = int(k)
          else: k = re.sub(r'\s+', ' ', k).strip()

          v = argmap.get(k, None)
          if v is not None:
            parts.append(v)
            continue

          if len(args) >= 2:
            ctx.expand_stack.append('ARG-DEFVAL')
            ret = expand_args(args[1], argmap)
            ctx.expand_stack.pop()
            parts.append(ret)
            continue

          # The argument is not defined (or name is empty)
          arg = _unexpanded_arg([str(k)], nowiki)
          parts.append(arg)
          continue

        if kind == 'L':
          # Link to another page
          new_args = list(expand_args(x, argmap)
                  for x in args)
          parts.append(_unexpanded_link(new_args, nowiki))
          continue

        if kind == 'E':
          # Link to another page
          new_args = [expand_args(x, argmap) for x in args]
          parts.append(_unexpanded_extlink(new_args, nowiki))
          continue

        if kind == 'N':
          parts.append(ch)
          continue

        ctx.error('expand_arg: unsupported cookie kind {!r} in {}'
                  .format(kind, m.group(0)))
        parts.append(m.group(0))

      parts.append(coded[pos:])

      return ''.join(parts)


    def expand_parserfn(fn_name, args):
      # Call parser function
      ctx.expand_stack.append(fn_name)
      expander = lambda arg: expand_recur(arg, parent)

      if fn_name == '#invoke': ret = invoke_fn(args, expander, parent)
      else: ret = call_parser_function(ctx, fn_name, args, expander)

      ctx.expand_stack.pop()  # fn_name
      # XXX if lua code calls frame:preprocess(), then we should
      # apparently encode and expand the return value, similarly to
      # template bodies (without argument expansion)
      # XXX current implementation of preprocess() does not match!!!
      return str(ret)

    # Main code of expand_recur()
    parts = []
    pos = 0
    for m in re.finditer(r'[{:c}-{:c}]'.format(MAGIC_FIRST, MAGIC_LAST), coded):
      new_pos = m.start()
      if new_pos > pos: parts.append(coded[pos:new_pos])

      pos = m.end()
      ch  = m.group(0)
      idx = ord(ch) - MAGIC_FIRST

      if not ctx.has_cookie(idx):
        parts.append(ch)
        continue

      kind, args, nowiki = ctx.load_cookie(idx)
      assert isinstance(args, tuple)

      if kind == 'T':
        if nowiki:
          parts.append(_unexpanded_template(args, nowiki))
          continue

        # Template transclusion or parser function call
        # Limit recursion depth
        if 100 <= len(ctx.expand_stack):
          ctx.error('recursion too deep during template expansion')
          parts.append('<strong class=\'error\'>too deep recursion '
                       'while expanding template {}</strong>'
                       .format(_unexpanded_template(args, True)))
          continue

        # Expand template/parserfn name
        ctx.expand_stack.append('TEMPLATE_NAME')
        tname = expand_recur(args[0], parent)
        ctx.expand_stack.pop()

        # Remove <noinclude/>
        tname = re.sub(r'<\s*noinclude\s*/\s*>', '', tname)

        # Strip safesubst: and subst: prefixes
        tname = tname.strip()
        if tname[:10].lower() == 'safesubst:': tname = tname[10:]
        elif tname[:6].lower() == 'subst:': tname = tname[6:]

        # Check if it is a parser function call
        ofs = tname.find(':')
        if 0 < ofs:
          # It might be a parser function call
          fn_name = ctx.name_data.canonicalize_parserfn_name(tname[:ofs])
          if fn_name in PARSER_FUNCTIONS or fn_name.startswith('#'):
            args = (tname[ofs + 1:].lstrip(),) + args[1:]
            parts.append(expand_parserfn(fn_name, args))
            continue

        # As a compatibility feature, recognize parser functions
        # also as the first argument of a template (without colon),
        # whether there are more arguments or not.  This is used
        # for magic words and some parser functions have an implicit
        # compatibility template that essentially does this.
        fn_name = ctx.name_data.canonicalize_parserfn_name(tname)
        if fn_name in PARSER_FUNCTIONS or fn_name.startswith('#'):
          parts.append(expand_parserfn(fn_name, args[1:]))
          continue

        # Otherwise it must be a template expansion
        body = ctx.get_template(tname)

        # Check for undefined templates
        if not body:
          parts.append('<strong class=\'error\'>Template:{}</strong>'
                       .format(html.escape(tname)))
          continue

        # If this template is not one of those we want to expand,
        # return it unexpanded (but with arguments possibly expanded)
        if not ctx.expand_template(tname):
          # Note: we will still expand parser functions in its
          # arguments, because those parser functions could
          # refer to its parent frame and fail if expanded
          # after eliminating the intermediate templates.
          new_args = [expand_recur(x, parent) for x in args]
          parts.append(_unexpanded_template(new_args, nowiki))
          continue

        # Construct and expand template arguments
        ctx.expand_stack.append(tname)
        ht = {}
        num = 1

        for i in range(1, len(args)):
          arg = str(args[i])
          m = re.match(r'(?s)^\s*([^][&<>="\']+?)\s*=\s*(.*?)\s*$', arg)
          if m:
            # Note: Whitespace is stripped by the regexp
            # around named parameter names and values per
            # https://en.wikipedia.org/wiki/Help:Template
            # (but not around unnamed parameters)
            k, arg = m.groups()
            if k.isdigit():
              k = int(k)
              if 1 < k or 1000 < k:
                ctx.debug('invalid argument number %d for template %r' % (
                  k, tname))
                k = 1000
              if num <= k: num = k + 1

            else:
              ctx.expand_stack.append('ARGNAME')
              k = expand_recur(k, parent)
              k = re.sub(r'\s+', ' ', k).strip()
              ctx.expand_stack.pop()

          else:
            k = num
            num += 1

          # Expand arguments in the context of the frame where
          # they are defined.  This makes a difference for
          # calls to #invoke within a template argument (the
          # parent frame would be different).
          ctx.expand_stack.append('ARGVAL-{}'.format(k))
          arg = expand_recur(arg, parent)
          ctx.expand_stack.pop()
          ht[k] = arg

        # Expand the body
        # XXX optimize by pre-encoding bodies during preprocessing
        # (Each template is typically used many times)
        # Determine if the template starts with a list item
        contains_list = re.match(r'(?s)^[#*;:]', body) is not None
        if contains_list: body = '\n' + body
        encoded_body = encode(ctx, body)

        # Expand template arguments recursively.  The arguments
        # are already expanded.
        encoded_body = expand_args(encoded_body, ht)

        # Expand the body using the calling template/page as
        # the parent frame for any parserfn calls
        new_title = tname.strip()
        if ctx.name_data.get(new_title) is None:
          new_title = ctx.name_data.get_name('Template') + ':' + new_title

        new_parent = (new_title, ht)
        # XXX no real need to expand here, it will expanded on
        # next iteration anyway (assuming parent unchanged)
        # Otherwise expand the body
        t = expand_recur(encoded_body, new_parent)

        assert isinstance(t, str)
        ctx.expand_stack.pop()  # template name
        parts.append(t)

      elif kind == 'A': parts.append(_unexpanded_arg(args, nowiki))

      elif kind == 'L':
        if nowiki: parts.append(_unexpanded_link(args, nowiki))
        else:
          # Link to another page
          ctx.expand_stack.append('[[link]]')
          new_args = [expand_recur(x, parent) for x in args]
          ctx.expand_stack.pop()
          parts.append(_unexpanded_link(new_args, nowiki))

      elif kind == 'E':
        if nowiki: parts.append(_unexpanded_extlink(args, nowiki))
        else:
          # Link to an external page
          ctx.expand_stack.append('[extlink]')
          new_args = [expand_recur(x, parent) for x in args]
          ctx.expand_stack.pop()
          parts.append(_unexpanded_extlink(new_args, nowiki))

      elif kind == 'N': parts.append(ch)

      else:
        ctx.error('expand: unsupported cookie kind {!r} in {}'
                  .format(kind, m.group(0)))
        parts.append(m.group(0))

    parts.append(coded[pos:])

    return ''.join(parts)

  # Encode all template calls, template arguments, and parser function
  # calls on the page.  This is an inside-out operation.
  encoded = encode(ctx, text)

  # Recursively expand templates.  This is an outside-in operation.
  expanded = expand_recur(encoded, parent)

  # Expand any remaining magic cookies and remove nowiki char
  expanded = finalize_expand(ctx, expanded)

  # Remove LanguageConverter markups:
  # https://www.mediawiki.org/wiki/Writing_systems/Syntax

  return expanded


def finalize_expand(ctx, text):
  '''Expands any remaining magic characters (to their original values)
  and removes nowiki characters.'''

  def magic_repl(m):
    idx = ord(m.group(0)) - MAGIC_FIRST
    if not ctx.has_cookie(idx): return m.group(0)
    kind, args, nowiki = ctx.load_cookie(idx)

    if kind == 'T': return _unexpanded_template(args, nowiki)
    if kind == 'A': return _unexpanded_arg(args, nowiki)
    if kind == 'L': return _unexpanded_link(args, nowiki)
    if kind == 'E': return _unexpanded_extlink(args, nowiki)
    if kind == 'N': return '<nowiki>' + args[0] + '</nowiki>'

    ctx.error('magic_repl: unsupported cookie kind {!r}'.format(kind))
    return ''

  # Keep expanding magic cookies until they have all been expanded.
  # We might get them from, e.g., unexpanded_template()
  while True:
    prev = text
    text = re.sub(
      r'[{:c}-{:c}]'.format(MAGIC_FIRST, MAGIC_LAST), magic_repl, text)

    if prev == text: break

  # Convert the special <nowiki /> character back to <nowiki />.
  # This is done at the end of normal expansion.
  return re.sub(MAGIC_NOWIKI_CHAR, '<nowiki />', text)


def preprocess_text(ctx, text):
  '''Preprocess the text by handling <nowiki> and comments.'''
  assert isinstance(text, str)

  def _nowiki_sub_fn(m):
    '''This function escapes the contents of a <nowiki> ... </nowiki> pair.'''
    text = m.group(1)
    return ctx.save_cookie('N', (text,), False)

  text = re.sub(r'(?si)<\s*nowiki\s*>(.*?)<\s*/\s*nowiki\s*>',
                _nowiki_sub_fn, text)
  text = re.sub(r'(?si)<\s*nowiki\s*/\s*>', MAGIC_NOWIKI_CHAR, text)
  text = re.sub(r'(?s)<!\s*--.*?--\s*>', '', text)

  return text
