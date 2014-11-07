from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from Products.agCommon.browser.views import FolderView
from plone.i18n.normalizer.interfaces import IIDNormalizer
from zope.component import getUtility
from zope.interface import implements, Interface

class EventProgramZIPView(FolderView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.programs = []
        self.zip_codes = []
        self.zip_radius = 0
        self.default_zip_radius = 50

    def publishTraverse(self, request, name):

        if name:
            if not self.programs:
                self.programs = self.lookupPrograms(name)
            elif not self.zip_codes:
                self.zip_codes = self.lookupZIPCodes(name)
            elif not self.zip_radius:
                self.zip_radius = self.lookupZIPRadius(name)

        return self

    @property
    def normalizer(self):
        return getUtility(IIDNormalizer)

    def lookupPrograms(self, p):
        all_program_values = self.portal_catalog.uniqueValuesFor('Topics')
        all_programs = dict([(self.normalizer.normalize(x), x) for x in all_program_values])
        programs = [all_programs.get(self.normalizer.normalize(x), '') for x in p.split('|')]
        return sorted([x for x in programs if x])

    def lookupZIPCodes(self, z):
        zip_codes = [self.zip_code_tool.toZIP5(x) for x in z.split('|')]
        return [x for x in zip_codes if x]

    def lookupZIPRadius(self, r):
        try:
            return int(r)
        except ValueError:
            return self.default_zip_radius

    def page_title(self):
        title = "Upcoming Events"
        page = ""
        if self.zip_radius:
            page = "%s for %s within %d miles of %s" % (title, ", ".join(self.programs), self.zip_radius, ", ".join(self.zip_codes))
        elif self.programs:
            page = "%s for %s" % (title, ", ".join(self.programs))
        else:
            return title

        return page

    @property
    def zip_code_tool(self):
        return getToolByName(self.context, 'extension_zipcode_tool')
            
    def getFolderContents(self):
        zips = []
        zip_radius = self.default_zip_radius
        if self.zip_radius:
            zip_radius = self.zip_radius
        for z in self.zip_codes:
            zips.extend(self.zip_code_tool.getNearbyZIPs(z, zip_radius))
        all_zips = self.portal_catalog.uniqueValuesFor('zip_code')
        search_zip_list = list(set(zips) & set(all_zips))
        search_zip_list.append('00000')

        query = {
                    'portal_type' : 'Event',
                    'end' : {'query' : DateTime(), 'range' : 'min'}, 
                    'sort_on' : 'start',
                }
        
        if self.zip_codes:
            query['zip_code'] = search_zip_list

        if self.programs:
            query['Topics'] = self.programs
            

        results = self.portal_catalog.queryCatalog(query)

        return results
