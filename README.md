gae-gitkit
==========

Google Identity Toolkit on App Engine for Python

This is a bare-bones example app of using Gitkit with App Engine for Python.

David Underhill's gae-sessions is used to manage sessions seemlessly behind a User model that mimics App Engine's own user api.

To get the demo working for yourself, you will have to make these adjustments:

* In main.py replace the dev and production values for SERVER_URL
* In appengine_config.py generate your own cookie key and replace the COOKIE_KEY value
* In gitkit.py replace the value for API_KEY
* In gitkit.py replace the contents of the <URI> tag in the XRDSHandler handler with your server address