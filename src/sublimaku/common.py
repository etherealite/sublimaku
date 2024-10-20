import requests

from subliminal import __short_version__


def session_factory(session: requests.Session) -> requests.Session:        
    session.headers['User-Agent'] = f'Subliminal/{__short_version__}'
    session.headers['Accept'] = 'application/json'
    session.headers['Content-Type'] = 'application/json'
    return session