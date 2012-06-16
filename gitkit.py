#!/usr/bin/env python
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from users import User, get_current_user
import os
import logging
import urllib2

try:
    import json
except:
    from django.utils import simplejson as json

_DEBUG = True

class CallbackHandler(webapp.RequestHandler):
    VERIFY_URL = 'https://www.googleapis.com/identitytoolkit/v1/relyingparty/verifyAssertion?key='
    #Insert your own Google developer API key here
    API_KEY = 'Your-dev-key-here'

    def get(self):
        self.get_or_post()

    def post(self):
        self.get_or_post()

    def get_or_post(self):
        requestUrl = self.request.environ['wsgi.url_scheme'] + '://' + \
             self.request.environ['HTTP_HOST'] + \
             self.request.environ['PATH_INFO'] + '?' + \
             self.request.environ['QUERY_STRING']


        idpPostBodyIO = self.request.environ['wsgi.input']
        postBody = idpPostBodyIO.read()
        #postBody = self.request.body
        if postBody == "":
            logging.warn("The callback request body is empty.")

        response = self.verify(requestUrl, postBody)

        if response:
            logging.info('Federated login success!')
            openid_values = self.get_openid_values(response)
            values = dict({
                'email':        openid_values.get('email'),
                'registered':   'true',
                'success':      True
            })

            self.render_gitkit(values)

            # fed_id changes (in gmail anyway) - use email for keyname...
            user = User.get_or_insert(openid_values.get('email'),
                                      display_name=openid_values.get('display_name'),
                                      fed_identity=openid_values.get('fed_identity'),
                                      fed_provider=openid_values.get('fed_provider'),
                                      photo_url=openid_values.get('photo_url')
                                      )
            # update the photo url, if needs be.
            if user.photo_url != openid_values.get('photo_url'):
                user.photo_url = openid_values.get('photo_url')
                user.put()

            user.login()
        else:
            logging.info('Problem with response from IDP')
            self.render_gitkit(success=False)

    def get_openid_values(self, response):
        values = {}
        values['email'] = response['verifiedEmail']
        values['fed_identity'] = response['identifier']
        values['fed_provider'] = response['authority']

        if 'displayName' in response and response['displayName'] != "None":
            values['display_name'] = response['displayName']
        else:
            values['display_name'] = values['email'].partition('@')[0]


        # FIXME... logic here a bit suspect
        if 'photoUrl' in response and response['photoUrl'] != "None" :
            values['photo_url'] = response['photoUrl']
        else:
            values['photo_url'] = None

        return values


    def _post_verify(self, postData):
        ''' Sends post HTTP request to the remote URL. '''

        try:
            params = json.dumps(postData)
            cookies = urllib2.HTTPCookieProcessor()
            opener = urllib2.build_opener(cookies)
            request = urllib2.Request(url = self.VERIFY_URL + self.API_KEY,
                                      headers = { 'Content-Type':
                                                  'application/json' },
                                      data = params)
            response = opener.open(request)
            out = response.read()
            return json.loads(out)
        except urllib2.URLError, e:
            logging.exception("URLerror in post_verify: %s", e)
            return None
        except Exception, e:
            logging.exception("Exception in post_verify: %s", e)
            return None

    def verify(self, url, postBody):
        '''Sends request to the identity toolkit API end point to verify the IDP
           response.

           Returns a json string of response from IDP
        '''
        try:
            data = {
              'requestUri': url,
              'postBody': postBody
            }
            response = self._post_verify(data)

            if response and 'verifiedEmail' in response:
                return response
            else:
                return None
        except Exception, e:
            logging.info(e)
            return None

    def render_gitkit(self, values = {}, success=True):
        '''Render the html that notifies gitkit of success/fail

           values is a dict that provides values to the template. Render a succes is
           default, set success=False to render a fail
        '''
        if success:
            func = ('window.google.identitytoolkit.notifyFederatedSuccess({ "email": "%s", "registered": %s });'
                % (values['email'], values['registered']))
        else:
            func = 'window.google.identitytoolkit.notifyFederatedError();'

        html = '''<!DOCTYPE html>
<html>
    <head>
        <script type='text/javascript' src='https://ajax.googleapis.com/jsapi'></script>
        <script type='text/javascript'>
          google.load("identitytoolkit", "1", {packages: ["notify"]});
        </script>
        <script type='text/javascript'>
        %s
        </script>
    </head>
    <body></body>
</html>''' % func

        self.response.out.write(html)

class LoginHandler(webapp.RequestHandler):
    '''If legacy login was allowed, this handles the request.

    But we're not allowed for now... maybe later.
    '''

    def get(self):
        self.error(403)

class LogoutHandler(webapp.RequestHandler):

    def get(self):
        user = get_current_user()

        #user may have timed out or not be logged in.
        if user:
            user.logout()

        self.redirect("/")

class StatusHandler(webapp.RequestHandler):
    '''Return response if email is already registered

    Request params: email=name@domain
    Response: {"registered": boolean}
    '''

    def post(self):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps({"registered": False}))

class SignupHandler(webapp.RequestHandler):
    '''Hangle the signup page...

    We're not going to allow legacy login
    We'll redirect to an explanation page.
    '''

    def get(self):
        self.redirect("/")

class XRDSHandler(webapp.RequestHandler):
    '''This response is required for the Aol login.

    From the forum, the location of this repsonse is set in a X-XRDS-Location
    response header. App engine kindly sets the header for you to /_ah/xrds
    '''

    def get(self):
        self.response.headers['Content-Type'] = "application/xrds+xml; charset=utf-8"
        self.response.out.write('''<?xml version="1.0" encoding="UTF-8"?>
<xrds:XRDS
  xmlns:xrds="xri://$xrds"
  xmlns:openid="http://openid.net/xmlns/1.0"
  xmlns="xri://$xrd*($v*2.0)">
  <XRD>

  <Service xmlns="xri://$xrd*($v*2.0)">
    <Type>http://specs.openid.net/auth/2.0/return_to</Type>
    <URI>http://gae-gitkit.appspot.com/callback</URI>
  </Service>

  </XRD>
</xrds:XRDS>''')

_URLS = [
  ('/callback', CallbackHandler),
  ('/login', LoginHandler),
  ('/logout', LogoutHandler),
  ('/status', StatusHandler),
  ('/signup', SignupHandler),
  ('/_ah/xrds', XRDSHandler)
]

def main():
    application = webapp.WSGIApplication(_URLS,
                                         debug=_DEBUG)
    util.run_wsgi_app(application)


if __name__ == '__main__':
  main()