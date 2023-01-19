import time


class PageProcTimer:
  def __init__(self, total = None):
    self.total = total
    self.start()


  def start(self):
    self.start = time.time()
    self.last = self.start
    self.count = 0


  def inc(self):
    self.count += 1
    now = time.time()

    if 1 < now - self.last:
      delta = now - self.start
      pps   = '{:,} pages/sec'.format(int(self.count / delta))

      if self.total:
        eta = delta / self.count * (self.total - self.count)

        remain = '{:02d}:{:02d}:{:02d}'.format(
          int(eta / 3600), int(eta / 60 % 60), int(eta % 60))

        percent = '{:.1%}'.format(self.count / self.total)

        print('  ... processed {:,} of {:,} pages ({}) @ {}, eta {}'.format(
          self.count, self.total, percent, pps, remain))

      else:

        print('  ... {:,} pages, {}'.format(self.count, pps))

      self.last = now
