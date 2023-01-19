class Namespace:
  def __init__(
    self, id = None, name = '', isSubject = False, isContent = False,
    isTalk = False, aliases = [], canonicalName = '', subject = None,
    talk = None):

    assert id is not None
    assert name

    self.id = id
    self.name = name
    self.isSubject = isSubject
    self.isContent = isContent
    self.isTalk = isTalk
    self.aliases = aliases
    self.canonicalName = canonicalName
    self.subject = subject
    self.talk = talk


  def match(self, name):
    if name and name.isdigit(): return int(name) == self.id

    name = name.lower()
    if self.name and name == self.name.lower(): return True
    if self.canonicalName and name == self.canonicalName.lower(): return True

    for a in self.aliases:
      if name == a.lower():
        return True

    return False
