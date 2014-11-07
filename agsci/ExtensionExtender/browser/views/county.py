from zope.interface import implements
from Products.CMFCore.utils import getToolByName
from Products.agCommon.browser.views import FolderView, IFolderView

try:
    from zope.app.component.hooks import getSite
except ImportError:
    from zope.component.hooks import getSite

class ByCountyView(FolderView):
    """
    By County browser view
    """
    implements(IFolderView)

    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.counties = []

        counties = {}

        results = []
        folder_path = ""

        self.here_url = self.context.absolute_url()

        if self.context.portal_type == 'Topic':
            try:
                results = self.context.queryCatalog()
            except AttributeError:
                # We don't like a relative path here for some reason.
                # Until we figure it out, fall through and just do the default query.
                # That should work in most cases.
                parent_physical_path = list(self.context.getPhysicalPath())
                parent_physical_path.pop()
                folder_path = '/'.join(parent_physical_path)
                pass

            # If we're a collection (Topic), we may be a default page  Figure out
            # if we're the default page, and if so, set the here_url to our parent.
            parent = self.context.getParentNode()
            if self.context.id == parent.getDefaultPage():
                self.here_url = parent.absolute_url()

        if not results:
            catalog = getToolByName(self.context, 'portal_catalog')

            if not folder_path:
                folder_path = '/'.join(self.context.getPhysicalPath())

            results = catalog.searchResults({'portal_type' : ['Event', 'TalkEvent', 'Person', 'News Item', 'Folder', 'Subsite', 'Section'],
                                            'path' : {'query': folder_path, 'depth' : 4} })
        for r in results:

            for county in r.extension_counties:

                if not counties.get(county):
                    counties[county] = {'id' : county.lower(),
                                     'label' : county, 'items' : []}


                counties[county]['items'].append(r)

        for c in sorted(counties.keys()):
            self.counties.append(counties[c])

    def getBodyText(self):
        return self.context.getBodyText()

    @property
    def portal_catalog(self):
        return getToolByName(self.context, 'portal_catalog')

    @property
    def portal(self):
        return getToolByName(self.context, 'portal_url').getPortalObject()


class ExtensionProgramCountyView(FolderView):
    """
    Program County browser view
    """
    implements(IFolderView)

    def __init__(self, context, request):
        self.context = context
        self.request = request

        programs = {}
        counties = {}

        portal_catalog = self.portal_catalog

        all_programs = self.request.form.get('program')

        if not all_programs:
            all_programs = portal_catalog.uniqueValuesFor('Topics')
        elif isinstance(all_programs, str):
            all_programs = [all_programs]

        all_counties = self.request.form.get('county')

        if not all_counties:
            all_counties = portal_catalog.uniqueValuesFor('Counties')
        elif isinstance(all_counties, str):
            all_counties = [all_counties]

        for p in all_programs:
            programs[p] = {}
            for c in all_counties:
                programs[p][c] = []

        for c in all_counties:
            counties[c] = {}
            for p in all_programs:
                counties[c][p] = []

        for r in portal_catalog.searchResults({'portal_type' : 'FSDPerson'}):
            for p in r.extension_topics:
                for c in r.extension_counties:
                    if p in all_programs and c in all_counties:
                        programs[p][c].append(r)
                        counties[c][p].append(r)

        self.by_program = programs
        self.by_county = counties

    def getBodyText(self):
        return self.context.getBodyText()

    @property
    def portal_catalog(self):
        return getToolByName(self.context, 'portal_catalog')

    @property
    def portal(self):
        return getToolByName(self.context, 'portal_url').getPortalObject()
