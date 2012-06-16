from google.appengine.ext import db
from gaesessions import get_current_session


class User(db.Model):
    # use email as key_name rather than prop.
    #email           = db.EmailProperty()
    display_name    = db.StringProperty()
    fed_identity    = db.LinkProperty()
    fed_provider    = db.LinkProperty()
    photo_url       = db.LinkProperty()
    
    def email(self):
        return self.key().name()
        
    def nickname(self):
        return self.display_name
        
    def user_id(self):
        return self.key()
        
    def federated_identity():
        return self.fed_identity
        
    def federated_provider():
        return self.fed_provider
    
    def login(self):
        '''Use gaesession to login and keep state
        
        '''
        session = get_current_session()
        if session.is_active():
            session.terminate()
            
        session.regenerate_id()
        session['user'] = self
        
    def logout(self):
        session = get_current_session()
        if session.has_key('user'):
            user = session['user']
            session.clear()
            session.terminate()


    
def get_current_user():
    '''Get the current user from the session
    
    '''
    session = get_current_session()
    
    if session and session.is_active():
        if session.has_key('user'):
            return session['user']
        else:
            raise RuntimeError
    else:
        return None