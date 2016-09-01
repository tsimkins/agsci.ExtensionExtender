from Products.agCommon.browser.viewlets import AgCommonViewlet
from Products.CMFCore.utils import getToolByName

class NewLocationViewlet(AgCommonViewlet):
    
    show_for_review_states = ['atlas-import-article',]
    hostname = 'cms.extension.psu.edu'
    
    def new_url(self):
        uid = self.context.UID()
        return 'https://%s/@@old_plone?UID=%s' % (self.hostname, uid)
    
    def show(self):
    
        if not self.anonymous:

            try:
                wftool = getToolByName(self.context, "portal_workflow")
                review_state = wftool.getInfoFor(self.context, 'review_state')
            except:
                return False
            else:
                return review_state in self.show_for_review_states
        
        return False