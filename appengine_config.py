from gaesessions import SessionMiddleware
import datetime
from config import COOKIE_KEY

def webapp_add_wsgi_middleware(app):
    app = SessionMiddleware(app, lifetime=datetime.timedelta(hours=1),cookie_key=COOKIE_KEY)
    return app