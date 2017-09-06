from Products.agCommon.browser.viewlets import AgCommonViewlet
from Products.CMFCore.utils import getToolByName

class NewLocationViewlet(AgCommonViewlet):

    show_for_review_states = [
                                'atlas-import-app',
                                'atlas-import-article', 
                                'atlas-import-curriculum',
                                'atlas-import-news-item',
                                'atlas-import-noop',
                                'atlas-import-online-course',
                                'atlas-import-publication', 
                                'atlas-import-smart-sheet',
                                'atlas-import-video',
                                'atlas-import-webinar',
                                'atlas-import-webinar-recording',
                                'atlas-import-workshop',
                                'atlas-import-workshop-group',
                             ]

    hostname = 'cms.extension.psu.edu'

    def new_url(self):
        uid = self.context.UID()
        return 'https://%s/@@old_plone?UID=%s' % (self.hostname, uid)

    def show(self):

        if not self.anonymous:

            wftool = getToolByName(self.context, "portal_workflow")

            # Check the review state of this object.  If it's not in the
            # 'show_for_review_states' list, return false
            try:
                review_state = wftool.getInfoFor(self.context, 'review_state')
            except:
                return False
            else:
                if review_state not in self.show_for_review_states:
                    return False

            # Check the review state of this parent object.  If it *IS* in the
            # 'show_for_review_states' list, return false
            parent = self.context.aq_parent

            try:
                review_state = wftool.getInfoFor(self.context.aq_parent, 'review_state')
            except:
                pass # Can't check, assume OK
            else:
                if review_state in self.show_for_review_states:
                    return False

            return True

        return False