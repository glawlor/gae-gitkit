#!/usr/bin/env python
import os
import webapp2
from google.appengine.ext.webapp import template
from users import get_current_user
from config import _DEBUG

class MainHandler(webapp2.RequestHandler):
    def get(self):
        user = get_current_user()
        values = {'user': user}
            
        path = os.path.join(os.path.dirname(__file__), 'templates', 'home.html')
        self.response.out.write(template.render(path, values, debug=_DEBUG))


app = webapp2.WSGIApplication([('/', MainHandler)], debug=_DEBUG)