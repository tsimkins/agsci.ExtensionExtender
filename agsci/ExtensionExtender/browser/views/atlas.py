from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from Products.agCommon.browser.views import FolderView
from plone.i18n.normalizer.interfaces import IIDNormalizer
from zope.component import getUtility
from zope.interface import implements, Interface, implementer
from zope.publisher.interfaces import IPublishTraverse
from zope.component.hooks import getSite
from Products.CMFPlone.interfaces import IPloneSiteRoot

@implementer(IPublishTraverse)
class AtlasContentReview(FolderView):

    review_state = ["atlas-pending", ]
    
    title = "Atlas Content Review: Owner Review"

    sections = ['animals', 'plants', 'pests', 'food', 'health', 
                'natural-resources', 'youth', 'community', 'business']

    content_types = ['PhotoFolder', 'Food', 'Link', 'File', 'Folder', 'Document',]

    @property
    def isPloneSite(self):
        return IPloneSiteRoot.providedBy(self.context)

    def publishTraverse(self, request, name):

        if name:
            self.user_id = name

        return self

    def getReviewStates(self):
        return ', '.join(self.review_state)

    def getUserId(self):

        user_id = getattr(self, 'user_id', None)
        
        if user_id:

            if user_id == 'all':
                return None

            return user_id
        
        portal_membership = getToolByName(self.context, 'portal_membership')
        user = portal_membership.getAuthenticatedMember()
        
        if user:
            return user.getId()
            
        return None

    def getReviewStructure(self):
    
        site_url = '/'.join(getSite().getPhysicalPath())
    
        paths = []
    
        pending = self.getReviewQueue()
        
        for r in pending:
            r_path = r.getPath().split('/')
            for i in range(len(site_url.split('/'))+1,len(r_path)+1):
                paths.append('/'.join(r_path[0:i]))

        results = self.portal_catalog.queryCatalog({'path' : {'query': paths, 'depth' : 0}})

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

        return self.portal_catalog.queryCatalog(query)

class AtlasPreReview(AtlasContentReview):

    review_state = ["published", ]
    
    title = "Atlas Content Review: Preliminary Review"

class AtlasFeedbackReview(AtlasContentReview):
    
    review_state = ["atlas-feedback", ]
    
    title = "Atlas Content Review: Owner Feedback Required"


class AtlasWebReview(AtlasContentReview):
    
    review_state = ["atlas-web-team-review", ]
    
    title = "Atlas Content Review: Web Team Review"
    
    def getUserId(self):
        return None

class AtlasReadyReview(AtlasWebReview):
    
    review_state = ["atlas-ready", ]
    
    title = "Atlas Content Review: Ready Content"

class AtlasInvalidOwner(AtlasWebReview):

    title = "Atlas Content Review: Invalid Owners"

    review_state = ['published', 'atlas-pending', 'atlas-web-team-review', 'atlas-feedback', 'atlas-ready']

    def getInvalidIds(self):

        valid_people = self.portal_catalog.queryCatalog({'portal_type' : 'FSDPerson', 'expires' : {'query' : DateTime(), 'range' : 'min'}})

        valid_people_ids = [x.getId for x in valid_people]
        
        creators = self.portal_catalog.uniqueValuesFor('Creator')
        
        return list(set(creators) - set(valid_people_ids))

    def getReviewQueue(self):

        query = {
            'review_state' : self.review_state
        }

        # Restrict query to content in team portions of site
        paths = self.getSectionPaths()

        if paths:
            query['path'] = paths

        invalid_ids = self.getInvalidIds()
        
        if invalid_ids:
            query['Creator'] = invalid_ids
            
        query['portal_type'] = self.content_types

        return self.portal_catalog.queryCatalog(query)

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
        
        