import re

from .common import MAGIC_FIRST, MAGIC_LAST, MAX_MAGICS, MAGIC_NOWIKI_CHAR


def encode(ctx, text):
  '''Encode all templates, template arguments, and parser function calls
  in the text, from innermost to outermost.'''

  def vbar_split(v):
    return list(m.group(1) for m in re.finditer(
      r'(?si)\|((<\s*([-a-zA-z0-9]+)\b[^>]*>[^][{}]*?<\s*/\s*\3\s*>|'
      r'[^|])*)', '|' + v))


  def repl_arg(m):
    '''Replacement function for template arguments.'''
    nowiki = m.group(0).find(MAGIC_NOWIKI_CHAR) >= 0
    orig = m.group(1)
    args = vbar_split(orig)

    return ctx.save_cookie('A', args, nowiki)


  def repl_arg_err(m):
    '''Replacement function for template arguments, with error.'''
    nowiki = m.group(0).find(MAGIC_NOWIKI_CHAR) >= 0
    prefix = m.group(1)
    orig = m.group(2)
    args = vbar_split(orig)

    # a single '}' needs to be escaped as '}}' with .format
    ctx.debug('heuristically added missing }} to template arg {}'
              .format(args[0].strip()))

    return prefix + ctx.save_cookie('A', args, nowiki)


  def repl_templ(m):
    '''Replacement function for templates {{name|...}} and parser functions.'''
    nowiki = m.group(0).find(MAGIC_NOWIKI_CHAR) >= 0
    v = m.group(1)
    args = vbar_split(v)

    return ctx.save_cookie('T', args, nowiki)


  def repl_templ_err(m):
    '''Replacement function for templates {{name|...}} and parser
    functions, with error.'''
    nowiki = m.group(0).find(MAGIC_NOWIKI_CHAR) >= 0
    prefix = m.group(1)
    v      = m.group(2)
    args   = vbar_split(v)

    # a single '}' needs to be escaped as '}}' with .format
    ctx.debug('heuristically added missing }} to template {}'
              .format(args[0].strip()))

    return prefix + ctx.save_cookie('T', args, nowiki)


  def repl_link(m):
    '''Replacement function for links [[...]].'''
    nowiki = m.group(0).find(MAGIC_NOWIKI_CHAR) >= 0
    orig   = m.group(1)
    args   = vbar_split(orig)

    return ctx.save_cookie('L', args, nowiki)


  def repl_extlink(m):
    '''Replacement function for external links [...].  This is also
    used to replace bracketed sections, such as [...].'''
    nowiki = m.group(0).find(MAGIC_NOWIKI_CHAR) >= 0
    orig   = m.group(1)
    args   = [orig]

    return ctx.save_cookie('E', args, nowiki)


  # Main loop of encoding.  We encode repeatedly, always the innermost
  # template, argument, or parser function call first.  We also encode
  # links as they affect the interpretation of templates.
  # As a preprocessing step, remove comments from the text.
  text = re.sub(r'(?s)<!\s*--.*?--\s*>', '', text)
  while True:
    prev = text

    # Encode template arguments.  We repeat this until there are
    # no more matches, because otherwise we could encode the two
    # innermost braces as a template transclusion.
    while True:
      prev2 = text

      # Encode links.
      while True:
        text = re.sub(
          r'(?s)\[' + MAGIC_NOWIKI_CHAR +
          r'?\[(([^][{}<>]|<[-+*a-zA-Z0-9]*>)+)\]' + MAGIC_NOWIKI_CHAR + r'?\]',
          repl_link, text)

        if text == prev2: break
        prev2 = text

      # Encode external links.
      text = re.sub(r'(?s)\[([^][{}<>|]+)\]', repl_extlink, text)

      # Encode template arguments
      text = re.sub(
        r'(?s)\{' + MAGIC_NOWIKI_CHAR + r'?\{' + MAGIC_NOWIKI_CHAR +
        r'?\{(([^{}]|\{\|[^{}]*\|\})*?)\}' + MAGIC_NOWIKI_CHAR + r'?\}' +
        MAGIC_NOWIKI_CHAR + r'?\}', repl_arg, text)

      if text == prev2:
        # When everything else has been done, see if we can find
        # template arguments that have one missing closing bracket.
        # This is so common in Wiktionary that I'm suspecting it
        # might be allowed by the MediaWiki parser.
        # This needs to be done before processing templates, as
        # otherwise the argument with a missing closing brace would
        # be interpreted as a template.
        text = re.sub(
          r'(?s)([^{])\{' + MAGIC_NOWIKI_CHAR + r'?\{' + MAGIC_NOWIKI_CHAR +
          r'?\{([^{}]*?)\}' + MAGIC_NOWIKI_CHAR + r'?\}', repl_arg_err, text)

        if text == prev2: break

    # Replace template invocation
    text = re.sub(
      r'(?si)\{' + MAGIC_NOWIKI_CHAR +
      r'?\{((\{\|[^{}]*?\|\}|\}[^{}]|[^{}](\{[^{}|])?)+?)\}' +
      MAGIC_NOWIKI_CHAR + r'?\}', repl_templ, text)

    # We keep looping until there is no change during the iteration
    if text == prev:
      # When everything else has been done, see if we can find
      # template calls that have one missing closing bracket.
      # This is so common in Wiktionary that I'm suspecting it
      # might be allowed by the MediaWiki parser.  We must allow
      # tables {| ... |} inside these.
      text = re.sub(
        r'(?s)([^{])\{' + MAGIC_NOWIKI_CHAR +
        r'?\{(([^{}]|\{\|[^{}]*\|\}|\}[^{}])+?)\}',
        repl_templ_err, text)

      if text != prev: continue
      # Replace remaining brackets and braces by corresponding
      # character entities
      # XXX
      break

    prev = text

  return text
