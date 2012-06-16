#!/usr/bin/env python
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from users import get_current_user
import os
import logging

_DEBUG = True

DEV = os.environ['SERVER_SOFTWARE'].startswith('Development')
if DEV:
    SERVER_URL = 'http://localhost:8085'
else:
    SERVER_URL = 'http://gae-gitkit.appspot.com'


class MainHandler(webapp.RequestHandler):
    def get(self):
        user = get_current_user()
        values = {'server_url': SERVER_URL, 'user': user}

        path = os.path.join(os.path.dirname(__file__), 'templates', 'home.html')
        self.response.out.write(template.render(path, values, debug=True))

def main():
    application = webapp.WSGIApplication([('/', MainHandler)],
                                         debug=_DEBUG)
    util.run_wsgi_app(application)


if __name__ == '__main__':
  main()