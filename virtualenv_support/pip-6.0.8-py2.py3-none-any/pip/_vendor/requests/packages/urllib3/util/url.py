from collections import namedtuple
from operator import itemgetter as _itemgetter
from ..exceptions import LocationParseError


url_attrs = ['scheme', 'auth', 'host', 'port', 'path', 'query', 'fragment']

class UrlT(tuple):
    'Url(scheme, auth, host, port, path, query, fragment)'

    __slots__ = ()

    _fields = ('scheme', 'auth', 'host', 'port', 'path', 'query', 'fragment')

    def __new__(_cls, scheme, auth, host, port, path, query, fragment):
        'Create new instance of Url(scheme, auth, host, port, path, query, fragment)'
        return tuple.__new__(_cls, (scheme, auth, host, port, path, query, fragment))

    @classmethod
    def _make(cls, iterable, new=tuple.__new__, len=len):
        'Make a new Url object from a sequence or iterable'
        result = new(cls, iterable)
        if len(result) != 7:
            raise TypeError('Expected 7 arguments, got %d' % len(result))
        return result

    def __repr__(self):
        'Return a nicely formatted representation string'
        return 'Url(scheme=%r, auth=%r, host=%r, port=%r, path=%r, query=%r, fragment=%r)' % self

    def _asdict(self):
        'Return a new OrderedDict which maps field names to their values'
        return OrderedDict(zip(self._fields, self))

    def _replace(_self, **kwds):
        'Return a new Url object replacing specified fields with new values'
        result = _self._make(map(kwds.pop, ('scheme', 'auth', 'host', 'port', 'path', 'query', 'fragment'), _self))
        if kwds:
            raise ValueError('Got unexpected field names: %r' % kwds.keys())
        return result

    def __getnewargs__(self):
        'Return self as a plain tuple.  Used by copy and pickle.'
        return tuple(self)

    __dict__ = property(_asdict)

    def __getstate__(self):
        'Exclude the OrderedDict from pickling'
        pass

    scheme = property(_itemgetter(0), doc='Alias for field number 0')

    auth = property(_itemgetter(1), doc='Alias for field number 1')

    host = property(_itemgetter(2), doc='Alias for field number 2')

    port = property(_itemgetter(3), doc='Alias for field number 3')

    path = property(_itemgetter(4), doc='Alias for field number 4')

    query = property(_itemgetter(5), doc='Alias for field number 5')

    fragment = property(_itemgetter(6), doc='Alias for field number 6')



# Pyston change:
class Url(UrlT):
#class Url(namedtuple('Url', url_attrs)):
    """
    Datastructure for representing an HTTP URL. Used as a return value for
    :func:`parse_url`.
    """
    slots = ()

    def __new__(cls, scheme=None, auth=None, host=None, port=None, path=None,
                query=None, fragment=None):
        return super(Url, cls).__new__(cls, scheme, auth, host, port, path,
                                       query, fragment)

    @property
    def hostname(self):
        """For backwards-compatibility with urlparse. We're nice like that."""
        return self.host

    @property
    def request_uri(self):
        """Absolute path including the query string."""
        uri = self.path or '/'

        if self.query is not None:
            uri += '?' + self.query

        return uri

    @property
    def netloc(self):
        """Network location including host and port"""
        if self.port:
            return '%s:%d' % (self.host, self.port)
        return self.host

    @property
    def url(self):
        """
        Convert self into a url

        This function should more or less round-trip with :func:`.parse_url`. The
        returned url may not be exactly the same as the url inputted to
        :func:`.parse_url`, but it should be equivalent by the RFC (e.g., urls
        with a blank port will have : removed).

        Example: ::

            >>> U = parse_url('http://google.com/mail/')
            >>> U.url
            'http://google.com/mail/'
            >>> Url('http', 'username:password', 'host.com', 80,
            ... '/path', 'query', 'fragment').url
            'http://username:password@host.com:80/path?query#fragment'
        """
        scheme, auth, host, port, path, query, fragment = self
        url = ''

        # We use "is not None" we want things to happen with empty strings (or 0 port)
        if scheme is not None:
            url += scheme + '://'
        if auth is not None:
            url += auth + '@'
        if host is not None:
            url += host
        if port is not None:
            url += ':' + str(port)
        if path is not None:
            url += path
        if query is not None:
            url += '?' + query
        if fragment is not None:
            url += '#' + fragment

        return url

    def __str__(self):
        return self.url

def split_first(s, delims):
    """
    Given a string and an iterable of delimiters, split on the first found
    delimiter. Return two split parts and the matched delimiter.

    If not found, then the first part is the full input string.

    Example::

        >>> split_first('foo/bar?baz', '?/=')
        ('foo', 'bar?baz', '/')
        >>> split_first('foo/bar?baz', '123')
        ('foo/bar?baz', '', None)

    Scales linearly with number of delims. Not ideal for large number of delims.
    """
    min_idx = None
    min_delim = None
    for d in delims:
        idx = s.find(d)
        if idx < 0:
            continue

        if min_idx is None or idx < min_idx:
            min_idx = idx
            min_delim = d

    if min_idx is None or min_idx < 0:
        return s, '', None

    return s[:min_idx], s[min_idx+1:], min_delim


def parse_url(url):
    """
    Given a url, return a parsed :class:`.Url` namedtuple. Best-effort is
    performed to parse incomplete urls. Fields not provided will be None.

    Partly backwards-compatible with :mod:`urlparse`.

    Example::

        >>> parse_url('http://google.com/mail/')
        Url(scheme='http', host='google.com', port=None, path='/mail/', ...)
        >>> parse_url('google.com:80')
        Url(scheme=None, host='google.com', port=80, path=None, ...)
        >>> parse_url('/foo?bar')
        Url(scheme=None, host=None, port=None, path='/foo', query='bar', ...)
    """

    # While this code has overlap with stdlib's urlparse, it is much
    # simplified for our needs and less annoying.
    # Additionally, this implementations does silly things to be optimal
    # on CPython.

    if not url:
        # Empty
        return Url()

    scheme = None
    auth = None
    host = None
    port = None
    path = None
    fragment = None
    query = None

    # Scheme
    if '://' in url:
        scheme, url = url.split('://', 1)

    # Find the earliest Authority Terminator
    # (http://tools.ietf.org/html/rfc3986#section-3.2)
    url, path_, delim = split_first(url, ['/', '?', '#'])

    if delim:
        # Reassemble the path
        path = delim + path_

    # Auth
    if '@' in url:
        # Last '@' denotes end of auth part
        auth, url = url.rsplit('@', 1)

    # IPv6
    if url and url[0] == '[':
        host, url = url.split(']', 1)
        host += ']'

    # Port
    if ':' in url:
        _host, port = url.split(':', 1)

        if not host:
            host = _host

        if port:
            # If given, ports must be integers.
            if not port.isdigit():
                raise LocationParseError(url)
            port = int(port)
        else:
            # Blank ports are cool, too. (rfc3986#section-3.2.3)
            port = None

    elif not host and url:
        host = url

    if not path:
        return Url(scheme, auth, host, port, path, query, fragment)

    # Fragment
    if '#' in path:
        path, fragment = path.split('#', 1)

    # Query
    if '?' in path:
        path, query = path.split('?', 1)

    return Url(scheme, auth, host, port, path, query, fragment)

def get_host(url):
    """
    Deprecated. Use :func:`.parse_url` instead.
    """
    p = parse_url(url)
    return p.scheme or 'http', p.hostname, p.port
