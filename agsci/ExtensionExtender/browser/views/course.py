from zope.interface import implements
from Products.CMFCore.utils import getToolByName
from Products.agCommon.browser.views import FolderView, IFolderView
from BeautifulSoup import BeautifulSoup
from plone.memoize.instance import memoize
from zope.component import getMultiAdapter
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

try:
    from zope.app.component.hooks import getSite
except ImportError:
    from zope.component.hooks import getSite

class BaseCourseView(FolderView):
    
    implements(IFolderView)
    
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def is_redirect(self):
        return getattr(self.context, 'extension_course_single_event', 'normal') == 'redirect'

    @property
    def is_alias(self):
        return getattr(self.context, 'extension_course_single_event', 'normal') == 'alias'

    @property
    def is_single_event(self):
        return len(self.topicContents()) == 1

    def getEventBrain(self):
        if self.is_single_event:
            return self.topicContents()[0]
        else:
            return None

    @memoize
    def topicContents(self):
        topicContents = []

        if self.context.portal_type in ['Topic']:
            topicContents = self.context.queryCatalog()

        return topicContents

                              
class CourseViewChooserView(BaseCourseView):

    def __call__(self):

        # Only do the single event query if one of the options is selected
        if (self.is_redirect or self.is_alias) and self.is_single_event:

            if self.is_redirect:
                return getMultiAdapter((self.context, self.request), 
                                        name=u'extension_course_annual_event_view')()
            elif self.is_alias:
                return getMultiAdapter((self.context, self.request), 
                                        name=u'extension_course_event_view')()

        return getMultiAdapter((self.context, self.request), 
                                name=u'extension_course_view')()

class CourseView(BaseCourseView):
    
    pass

class CourseAnnualEventView(BaseCourseView):

    def __call__(self, *args, **kw):

        if self.anonymous:
            return self.request.RESPONSE.redirect(self.getEventBrain().getURL())
        else:
            return self.index(*args, **kw)
                    

class CourseEventView(BaseCourseView):
    
    @memoize
    def event_soup(self):
        topicContents = self.topicContents()
        if len(topicContents) == 1:
            o = topicContents[0].getObject()
            if o.portal_type == 'Event':
                html = o.event_view()
                soup = BeautifulSoup(html)
                return soup
        return None
    
    def leadimage(self):
        soup = self.event_soup()
        if soup:
            leadimage = soup.find(attrs={'class' : 'contentLeadImageContainer'})
            if leadimage:
                return repr(leadimage)      
    
    def content_core(self):
        soup = self.event_soup()
#        import pdb; pdb.set_trace()
        if soup:
            core = soup.find(id='content-core')
            if core:
                core['id'] = ''
                for div in core.findAll(attrs={'class' : 'eventWebsite'}):
                    div.extract()
                for div in core.findAll(attrs={'id' : 'addthis'}):
                    div.extract()
                return repr(core)
        return ''
