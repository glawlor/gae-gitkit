#!/usr/bin/env python
import webapp2
import os
import logging
import urllib2
from google.appengine.ext.webapp import template
from users import User, get_current_user
from config import SERVER_URL, API_KEY, _DEBUG

try:
    import json
except:
    from django.utils import simplejson as json


class CallbackHandler(webapp2.RequestHandler):
    VERIFY_URL = 'https://www.googleapis.com/identitytoolkit/v1/relyingparty/verifyAssertion?key='

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

            self.render_gitkit(openid_values)

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

            request = urllib2.Request(url = self.VERIFY_URL + API_KEY,
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

    def render_gitkit(self, values = {}):
        '''Render the html that notifies gitkit of success/fail

           values is a dict that provides values to the template. Render a succes is
           default, set success=False to render a fail
        '''


        html = '''<!DOCTYPE html>
<html>
    <head>
        <script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/1.4.2/jquery.min.js"></script>
        <script type="text/javascript" src="https://ajax.googleapis.com/jsapi"></script>
        <script type="text/javascript" src="https://www.accountchooser.com/client.js"></script>
        <script type="text/javascript">
          google.load('identitytoolkit', '2', {packages: ['store']});
          jQuery(function() {
            var homeUrl = '%s'; // Your home page URL.
            var account = {
              email: '%s',  // required
              displayName: '%s',  // optional
              photoUrl: '%s'  // optional
            };
            // Store the account then return to homeUrl.
            window.google.identitytoolkit.storeAccount(account, homeUrl);
          });
        </script>
    </head>
    <body></body>
</html>
        ''' % (SERVER_URL, values['email'], values['display_name'], values['photo_url'])

        self.response.out.write(html)

class LegacyLoginHandler(webapp2.RequestHandler):
    '''If legacy login was allowed, this handles the request.

    But we're not allowed for now... maybe later.
    '''

    def get(self):
        self.error(403)
        
class LoginHandler(webapp2.RequestHandler):
    def get(self):
        user = get_current_user()
        values = {'server_url': SERVER_URL, 'api_key': API_KEY, 'user': user}
            
        path = os.path.join(os.path.dirname(__file__), 'templates', 'login.html')
        self.response.out.write(template.render(path, values, debug=True))

class LogoutHandler(webapp2.RequestHandler):

    def get(self):
        user = get_current_user()

        #user may have timed out or not be logged in.
        if user:
            user.logout()

        self.redirect("/")

class StatusHandler(webapp2.RequestHandler):
    '''Return response if email is already registered

    Request params: email=name@domain
    Response: {"registered": boolean}
    '''

    def post(self):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps({"registered": False}))


class SignupHandler(webapp2.RequestHandler):
    '''Handle the signup page...

    We're not going to allow legacy login
    We'll redirect to an explanation page.
    '''

    def get(self):
        self.redirect("/")

class XRDSHandler(webapp2.RequestHandler):
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
    <URI>{0}/callback</URI>
  </Service>

  </XRD>
</xrds:XRDS>'''.format(SERVER_URL))

_URLS = [
  ('/callback', CallbackHandler),
  ('/legacylogin', LegacyLoginHandler),
  ('/login', LoginHandler),
  ('/logout', LogoutHandler),
  ('/status', StatusHandler),
  ('/signup', SignupHandler),
  ('/_ah/xrds', XRDSHandler)
]

app = webapp2.WSGIApplication(_URLS,
                              debug=_DEBUG)

