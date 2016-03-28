from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from Products.agCommon.browser.views import FolderView
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.memoize.instance import memoize
from zope.component import getUtility
from zope.interface import implements, Interface, implementer
from zope.publisher.interfaces import IPublishTraverse
from zope.component.hooks import getSite
from Products.CMFPlone.interfaces import IPloneSiteRoot

try:
    from plone.protect.utils import addTokenToUrl
except ImportError:
    def addTokenToUrl(x):
        return x

@implementer(IPublishTraverse)
class AtlasContentReview(FolderView):

    review_state = ["atlas-pending", ]
    
    app_title = "Atlas Content Review"

    sections = ['animals', 'plants', 'pests', 'food', 'health', 
                'natural-resources', 'youth', 'community', 'business']

    content_types = ['PhotoFolder', 'Food', 'Link', 'File', 'Folder', 'Document',]

    view_titles = {
        'atlas_owner_review' : 'Owner Review',
        'atlas_web_review' : 'Web Team Review',
        'atlas_ready_review' : 'Ready Content',
        'atlas_feedback_review' : 'Owner Feedback',
        'atlas_invalid_owner' : 'Invalid Owners',
        'atlas_pre_review' : 'Preliminary Review',
        'atlas_archive_review' : 'Archived Content',
    }

    default_nav = [
                    'atlas_owner_review', 'atlas_feedback_review', 
                    'atlas_ready_review', 'atlas_archive_review'
                  ]

    nav_items_by_role = {
        'Atlas Manager' : [
                            'atlas_owner_review', 'atlas_pre_review', 
                            'atlas_invalid_owner', 'atlas_web_review', 
                            'atlas_feedback_review', 'atlas_ready_review',
                            'atlas_archive_review'
                        ],
        'Atlas Content Manager' : [
                            'atlas_owner_review',  
                            'atlas_invalid_owner',  
                            'atlas_feedback_review', 
                            'atlas_ready_review',
                            'atlas_archive_review' 
                        ],
    }

    show_actions = False

    @property
    def portal_membership(self):
        return getToolByName(self.context, 'portal_membership')

    @property
    def portal_workflow(self):
        return getToolByName(self.context, 'portal_workflow')

    def addTokenToUrl(self, url):
        return addTokenToUrl(url)

    def getWorkflowActions(self, brain=None):
        if brain and hasattr(brain, 'getObject'):
            obj = brain.getObject()

            transitions = self.portal_workflow.getTransitionsFor(obj)

            return [x for x in transitions if 'atlas' in x.get('id', '')]

        return []

    def needsReview(self, brain=None):
        if brain:
        
            if brain.portal_type in ['Subsite', 'Section', 'Blog']:
                return False
            
            review_state_match = (brain.review_state in self.review_state)
            
            user_id = self.getUserId()
            
            if user_id:
                return (brain.Creator == user_id) and review_state_match
            
            return review_state_match

        return False

    def getReviewStateClass(self, brain=None):
        if brain:
            if len(self.review_state) > 1:
                return 'state-%s' % brain.review_state
            
        return ''
        
    def getItemURL(self, brain=None):
        if brain:
            return brain.getURL()
            
        return None

    def getNavigationItemData(self, view_name):

        url = '%s/@@%s' % (self.context.absolute_url(), view_name)

        return (url, self.getViewTitle(view_name), (self.__name__ == view_name))

    def getNavigationItemsByRole(self):
        role = self.getAtlasRole()
        
        return self.nav_items_by_role.get(role, self.default_nav)

    def navigation_items(self):

        user_id = getattr(self, 'user_id', None) 

        return [self.getNavigationItemData(x) for x in self.getNavigationItemsByRole()]

    def getViewTitle(self, view_name=None):
        if not view_name:
            view_name = self.__name__

        return self.view_titles.get(view_name, 'N/A')

    @property
    def title(self):
        return '%s: %s' % (self.app_title, self.getViewTitle())

    @property
    def isPloneSite(self):
        return IPloneSiteRoot.providedBy(self.context)

    def publishTraverse(self, request, name):

        if name:
            self.user_id = name

        return self

    def getReviewStates(self):
        return ', '.join(self.review_state)

    @memoize
    def getUserId(self):

        user_id = getattr(self, 'user_id', self.request.form.get('user_id', None))
        
        if user_id:

            if user_id == 'all':
                return None

            return user_id
        
        if not self.isPowerUser():
            user = self.portal_membership.getAuthenticatedMember()
            
            if user:
                return user.getId()
            
        return None


    @memoize
    def getAtlasRole(self):
        atlas_roles = ['Atlas Manager', 'Atlas Content Manager']
    
        user = self.portal_membership.getAuthenticatedMember()
        
        user_roles = filter(lambda x:atlas_roles.count(x), user.getRolesInContext(self.context))
        
        try:
            return user_roles[0]
        except IndexError:
            return None


    def showOwnerFilter(self):
        if self.getUserId():
            return False
        
        if not self.getReviewQueueOwners():
            return False
    
        return self.isPowerUser()


    def isPowerUser(self):
        return (self.isAtlasManager() or self.isAtlasContentManager())

        
    def isAtlasManager(self):
        return (self.getAtlasRole() == 'Atlas Manager')


    def isAtlasContentManager(self):
        return (self.getAtlasRole() == 'Atlas Content Manager')

    @memoize
    def getReviewStructure(self):
    
        site_url = '/'.join(getSite().getPhysicalPath())
    
        paths = []
    
        pending = self.getReviewQueue()
        
        for r in pending:
            r_path = r.getPath().split('/')
            for i in range(len(site_url.split('/'))+1,len(r_path)+1):
                paths.append('/'.join(r_path[0:i]))

        results = self.portal_catalog.searchResults({'path' : {'query': paths, 'depth' : 0}})

        bh = BrainHierarchy(site_url)

        for r in results:
            bh.add(r)
        
        return bh.getStructure(bh.getRootPaths())


    def getSectionPaths(self):
        
        if self.isPloneSite:

            site = getSite()
            return ['/'.join(site[x].getPhysicalPath()) for x in self.sections]
        
        else:
            return '/'.join(self.context.getPhysicalPath())

    @memoize
    def getReviewQueue(self):

        query = {
            'review_state' : self.review_state,
        }

        # Restrict query to content in team portions of site
        paths = self.getSectionPaths()

        if paths:
            query['path'] = paths

        user_id = self.getUserId()
        
        if user_id:
            query['Creator'] = user_id

        query['portal_type'] = self.content_types

        return self.portal_catalog.searchResults(query)

    @memoize
    def getValidIds(self):
    
        valid_people = self.portal_catalog.searchResults({'portal_type' : 'FSDPerson', 'expires' : {'query' : DateTime(), 'range' : 'min'}})

        return [x.getId for x in valid_people]

    @memoize
    def getInvalidIds(self):

        valid_people_ids = self.getValidIds()
        
        creators = self.portal_catalog.uniqueValuesFor('Creator')
        
        return list(set(creators) - set(valid_people_ids))

    def getReviewQueueOwners(self):
        return set([x.Creator for x in self.getReviewQueue()])


class AtlasFeedbackReview(AtlasContentReview):
    
    review_state = ["atlas-feedback", ]
    

class AtlasWebReview(AtlasContentReview):
    
    review_state = ["atlas-web-team-review", ]


class AtlasPreReview(AtlasWebReview):

    review_state = ["published", ]
    
    show_actions = True


class AtlasReadyReview(AtlasWebReview):
    
    review_state = ["atlas-ready", ]

class AtlasArchiveReview(AtlasWebReview):
    
    review_state = ["atlas-archive", ]
    
    
class AtlasInvalidOwner(AtlasWebReview):

    review_state = ['published', 'atlas-pending', 'atlas-web-team-review', 'atlas-feedback', 'atlas-ready']

    show_actions = True

    def getItemURL(self, brain=None):
        if brain:
            url = super(AtlasInvalidOwner, self).getItemURL(brain=brain)
            url = addTokenToUrl('%s/edit' % url)
            return '%s#fieldsetlegend-ownership' % url
            
        return None

    def getWorkflowActions(self, brain=None):
    
        if brain and hasattr(brain, 'getObject'):

            # Only show Atlas Archive action for invalid owner view
            transitions = super(AtlasInvalidOwner, self).getWorkflowActions(brain=brain)
            return [x for x in transitions if 'archive' in x.get('id', '')]

        return []

    def needsReview(self, brain=None):
    
        if brain:

            # If we otherwise need to review this, also check to make sure that the owner is invalid.
            if super(AtlasInvalidOwner, self).needsReview(brain=brain):
                return (brain.Creator not in self.getValidIds())
            
        return False

    @memoize
    def getReviewQueue(self):

        query = {
            'review_state' : self.review_state
        }

        # Restrict query to content in team portions of site
        paths = self.getSectionPaths()

        if paths:
            query['path'] = paths

        invalid_ids = self.getInvalidIds()
        user_id = self.getUserId()

        if user_id:
            query['Creator'] = user_id        
        elif invalid_ids:
            query['Creator'] = invalid_ids
            
        query['portal_type'] = self.content_types

        return self.portal_catalog.searchResults(query)

class BrainHierarchy(object):

    def __init__(self, site_url):
        self.site_url=site_url
        self.items = {}
        self.children = {}    

    def site_url(self):
        return '/'.join(self.site.getPhysicalPath())
    
    def add(self, brain):
        # Get path of self and parent
        brain_path = brain.getPath()[len(self.site_url)+1:]
        brain_parent_path = '/'.join(brain_path.split('/')[0:-1])
        
        # Add brain_path to brain
        self.items[brain_path] = brain

        # Create an entry for self children
        if not self.children.has_key(brain_path):
            self.children[brain_path] = []
        
        # Create/update an entry for self parent children
        if not self.children.has_key(brain_parent_path):
            self.children[brain_parent_path] = []
            
        self.children[brain_parent_path].append(brain_path)
        
        return True
    
    def getRootPaths(self):
        return [x for x in self.items.keys() if '/' not in x]
    
    def getStructure(self, paths=[]):

        data = []
            
        for p in paths:
            data.append({'path' : p, 'brain' : self.items.get(p), 'children' : self.getStructure(self.children[p])})
        
        return data
        
class AtlasGenericRedirect(AtlasContentReview):

    def __call__(self):
        context = self.context
        
        if self.isDefaultPage():
            context = self.context.aq_parent
    
        url = '%s/@@atlas_owner_review' % context.absolute_url()

        if self.isAtlasManager():
            url = '%s/@@atlas_web_review' % context.absolute_url()

        return self.context.REQUEST.RESPONSE.redirect(url)