import time
import traceback
import multiprocessing
import pkg_resources

from .mediawikisax    import MediaWikiSAX
from .cache           import PageCache
from .context         import Context
from .namespace_data  import NamespaceData
from .page_proc_timer import PageProcTimer


def _handler(*args, **kwargs):
  global _global_page_handler
  return _global_page_handler(*args, **kwargs)


class WikiMunge:
  def __init__(self, lang, outdir, template_filter = None, log = None,
               threads = None):
    self.threads = threads

    # Log
    if isinstance(log, str): log = open(log, 'w')

    # Namespace data
    path = 'namespaces/%s.json' % lang
    path = pkg_resources.resource_filename('wikimunge', path)
    self.name_data = NamespaceData(path)

    self.cache = PageCache(self.name_data, outdir)
    self.ctx   = Context(self.name_data, self.cache,
                         template_filter = template_filter, log = log)


  def parse(self, title, text):
    self.ctx.start_page(title)
    return self.ctx.parse(text)


  def expand(self, title, text):
    self.ctx.start_page(title)
    return self.ctx.expand(text)


  def add_page(self, model, title, text):
    self.cache.add(model, title, text)


  def reprocess(self, queue, page_handler):
    global _global_page_handler

    def local_handler(title):
      try:
        text = self.cache.read(title)
        return True, page_handler(title, text)

      except Exception as e:
        trace = ''.join(traceback.format_exception(
          type(e), value = e, tb = e.__traceback__))
        return False, 'Exception in %s:\n%s' % (title, trace)

    _global_page_handler = local_handler

    pool  = multiprocessing.Pool(self.threads)
    timer = PageProcTimer(len(queue))

    for success, ret in pool.imap_unordered(_handler, queue):
      if not success: print(ret)
      elif ret is not None: yield ret

      timer.inc()

    pool.close()
    pool.join()


  def process(self, path, page_handler):
    # Load pages
    timer = PageProcTimer()

    def handler(*args):
      page_handler(*args)
      timer.inc()

    MediaWikiSAX().parse(path, handler)

    # Redirect Templates
    self.cache.redirect_templates()

    # Save cache
    self.cache.save()
