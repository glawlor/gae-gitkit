from gaesessions import SessionMiddleware
import datetime

#generate your own cookie key here
#Tip:
#In a python interpreter you can use "os.urandom(64).encode('base64')"
COOKIE_KEY = 'your-generated-cookie-key'

def webapp_add_wsgi_middleware(app):
    app = SessionMiddleware(app, lifetime=datetime.timedelta(hours=1),cookie_key=COOKIE_KEY)
    return app