from zope import schema
from zope.component import getMultiAdapter
from zope.formlib import form
from zope.interface import implements
from plone.memoize.compress import xhtml_compress

from plone.app.portlets.portlets import base
from plone.memoize.instance import memoize
from plone.portlets.interfaces import IPortletDataProvider
from plone.app.portlets.cache import render_cachekey

from Acquisition import aq_chain, aq_inner
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFPlone import PloneMessageFactory as _
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces import IFolderish
from Products.CMFPlone.interfaces import IPloneSiteRoot

from agsci.subsite.portlet.tags import Assignment as TagsAssignment
from agsci.subsite.portlet.tags import Renderer as TagsRenderer

from zope.component import getUtility
from plone.i18n.normalizer.interfaces import IIDNormalizer

from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.schema.interfaces import IVocabularyFactory

class TypesVocabulary(object):
    """Vocabulary factory for fields.
    """
    implements(IVocabularyFactory)

    def __call__(self, context):
        return SimpleVocabulary([
            SimpleTerm('extension_counties', title="County"),
            SimpleTerm('extension_courses', title="Course"),
            SimpleTerm('extension_topics', title="Program"),
            SimpleTerm('extension_subtopics', title="Topic"),
        ])

TypesVocabularyFactory = TypesVocabulary()

class IDrilldown(IPortletDataProvider):

    header = schema.TextLine(
        title=_(u"Portlet header"),
        description=_(u"Title of the rendered portlet"),
        required=True)

    drilldown_type = schema.Choice(
            title=_(u"heading_drilldown_type",
                default=u"Field"),
            description=_(u"description_drilldown_type",
                default=u"Field on which to drill down"),
            required=False,
            vocabulary='agsci.ExtensionExtender.portlet.drilldown.types'
    )

    show_header = schema.Bool(
        title=_(u"Show portlet header"),
        description=_(u""),
        required=False,
        default=True)

    dropdown = schema.Bool(
        title=_(u"Show dropdown"),
        description=_(u"Show dropdown rather than listing all items."),
        required=False,
        default=False)

class Assignment(TagsAssignment):

    implements(IDrilldown)

    header = ""
    show_header = False
    dropdown = False
    drilldown_type = None

    def __init__(self, header=u"", show_header=False, drilldown_type=None, dropdown=False, *args, **kwargs):
        base.Assignment.__init__(self, *args, **kwargs)
        self.header = header
        self.show_header = show_header
        self.data.drilldown_type = drilldown_type
        self.dropdown = dropdown
                
    @property
    def title(self):
        if self.header:
            return self.header
        else:
            return "Drilldown"


class Renderer(TagsRenderer):
    _template = ViewPageTemplateFile('templates/drilldown.pt')

    def __init__(self, *args):
        base.Renderer.__init__(self, *args)

    @property 
    def obj_tags(self):
        return {
            'extension_counties' : 'extension_counties',
            'extension_courses' : 'extension_courses',
            'extension_topics' : 'extension_topics',
            'extension_subtopics' : 'extension_subtopics',
        }.get(self.data.drilldown_type, 'unknown')

    @property 
    def target_view(self):
        return {
            'extension_counties' : 'counties',
            'extension_courses' : 'course',
            'extension_topics' : 'programs',
            'extension_subtopics' : 'topics',
        }.get(self.data.drilldown_type, 'unknown')

    @property 
    def catalog_index(self):
        return {
            'extension_counties' : 'Counties',
            'extension_courses' : 'Courses',
            'extension_topics' : 'Topics',
            'extension_subtopics' : 'Subtopics',
        }.get(self.data.drilldown_type, 'unknown')

    @property
    def parent_object(self):
       
        # parent_object is the portlet's parent
        # Default to self.context
        parent_object = self.context
        
        # If context is the default page, set parent_object to parentNode
        parentNode = aq_inner(self.context).getParentNode()
        
        if hasattr(parentNode, 'getDefaultPage') and parentNode.getDefaultPage() == self.context.getId():
            parent_object = parentNode

        return parent_object

    @property
    def drilldown_label(self):
        vocab = TypesVocabulary()
        try:
            label = vocab(self.context).getTermByToken(self.data.drilldown_type)
            return label.title
        except LookupError:
            return ''


    @property
    def available_tags(self):
        tags = list(self.portal_catalog.uniqueValuesFor(self.catalog_index))

        for v in ['', 'N/A']:
            if v in tags:
                tags.remove(v)

        return tags

    @property
    def tag_root(self):
        return self.parent_object


    
    @property
    def tags(self):
        return self.memoized_tags()

    @memoize
    def memoized_tags(self):
        normalizer = getUtility(IIDNormalizer)
        tag_root = self.tag_root
        
        available_tags = self.available_tags
        tags = {}
        normalized_tags = []

        if self.context.portal_type == 'Topic':
            items = self.context.queryCatalog()
        else:                
            path = '/'.join(tag_root.getPhysicalPath())
            items = self.portal_catalog.searchResults({self.catalog_index : available_tags, 'path' : path})                

        for i in items:
            if hasattr(i, self.obj_tags) and getattr(i, self.obj_tags):
                for t in getattr(i, self.obj_tags):
                    if available_tags:
                        if t in available_tags:
                            tags[t] = 1
                    elif t:
                        tags[t] = 1
       
        for t in sorted(tags.keys()):
            normalized_tags.append([normalizer.normalize(t), t])    

        return normalized_tags

    def render(self):
        return xhtml_compress(self._template())

    @property
    def available(self):
        return self.tags


class AddForm(base.AddForm):
    form_fields = form.Fields(IDrilldown)
    label = _(u"Add Drilldown Portlet")
    description = _(u"This portlet displays drilldown information for Extension custom fields.")

    def create(self, data):
        return Assignment(**data)

class EditForm(base.EditForm):
    form_fields = form.Fields(IDrilldown)
    label = _(u"Edit Drilldown Portlet")
    description = _(u"This portlet displays drilldown information for Extension custom fields.")
