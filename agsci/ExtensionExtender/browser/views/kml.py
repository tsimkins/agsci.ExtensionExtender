from AccessControl import ClassSecurityInfo
from StringIO import StringIO
from Products.CMFCore import permissions
from zope.interface import implements, Interface
from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from lxml import etree
from Products.CMFPlone.browser.ploneview import Plone
from DateTime import DateTime
from zope.component import getUtility
from plone.i18n.normalizer.interfaces import IIDNormalizer
from zope.publisher.interfaces import IPublishTraverse

try:
    from zope.app.component.hooks import getSite
except ImportError:
    from zope.component.hooks import getSite

import zipfile
import random

class KMLView(Plone):

    implements(IPublishTraverse)

    def __init__(self, context, request, show_all=False):
        self.context = context
        self.request = request
        self.show_all = show_all
        self.filter_program = None

    @property
    def colors(self):

        return {
            'Community and Business': 'FF8C2F',
            'Animals': 'CF1919',
            'Natural Resources': '4ADF1B',
            'Plants and Pests': '298DDF',
            'Food and Health': 'FFE04F',
            'Youth and Family': 'B745DF',
            'None': 'ffffff',
        }
    
    @property
    def programs(self):
        return self.colors.keys()

    @property
    def normalizer(self):
        return getUtility(IIDNormalizer)

    def normalize(self, i):
        return self.normalizer.normalize(i)

    def publishTraverse(self, request, name):

        self.filter_program = None

        if name:
            t = [x for x in self.programs if self.normalize(x) == name]

            if t:
                self.filter_program = t[0]

        return self

    def error(self, msg):
        self.request.response.setHeader('Content-Type', 'text/plain')
        return "Error: %s" % msg

    def getStyles(self):

        styles = []

        for k in sorted(self.colors.keys()):
            v = self.colors[k]

            style_id = self.normalize(k)

            style = etree.Element("Style", id="style-%s" % style_id)

            icon_style = etree.Element("IconStyle")

            color = etree.Element("color")
            color.text = "ff%s%s%s" % (v[4:6], v[2:4], v[0:2])
            icon_style.append(color)

            scale = etree.Element("scale")
            scale.text = "1.0"
            icon_style.append(scale)

            icon = etree.Element("Icon")

            href = etree.Element("href")
            href.text = "%s/placemark_circle.png" % getSite().absolute_url()

            icon.append(href)

            icon_style.append(icon)

            style.append(icon_style)

            styles.append(style)

        return styles

    def __call__(self):

        # Data Structures
        folders = {}

        # Find ZIP Code Tool
        ezt = getToolByName(self.context, "extension_zipcode_tool", None)

        if not ezt:
            return self.error("ZIP Code Tool Not Found")

        # Establish context
        context = self.context

        # Operate on default page if called on a folder
        if context.getDefaultPage() in context.objectIds():
            context = context[context.getDefaultPage()]

        if not hasattr(context, "queryCatalog") or not hasattr(context, "buildQuery"):
            return self.error("Not operating on a collection")

        # Begin KML Document
        kml = etree.Element("kml", xmlns="http://www.opengis.net/kml/2.2")

        d = etree.Element("Document")

        # Append placemarks tyles
        for s in self.getStyles():
            d.append(s)

        # Create a folder for each program
        # Don't append yet, ensure that they have contents.

        for t in self.programs:
            folder = etree.Element("Folder")
            folder_name = etree.Element("name")
            folder_name.text = t
            folder.append(folder_name)
            folders[t] = folder

        # Get results depending if show_all is set.
        # show_all removes the date criteria from the query
        # and pulls events in the past year.
        if self.show_all:
            portal_catalog = getToolByName(self.context, 'portal_catalog')
            query = context.buildQuery()
            if 'end' in query.keys():
                del query['end']
            query['start'] = {'query': DateTime()-365, 'range': 'min'}
            results = portal_catalog.searchResults(query)
        else:
            results = context.queryCatalog()

        # Cycle through results and create Placemark
        for r in results:
        
            # Look up ZIP Code
            zip_code = r.zip_code
            info = ezt.getZIPInfo(zip_code)

            # Skip if no ZIP lookup
            if not info:
                continue
            
            # Determine program                
            program = "None"

            if r.extension_topics:
                programs = sorted(list(set([x.split(':')[0] for x in r.extension_topics])))
                
                if len(programs) > 1:
                    # Figure out which program this falls under
                    if self.filter_program and self.filter_program in programs:
                        program = self.filter_program
                    else:
                        # Just pick one at random
                        program = random.choice(programs)
                else:
                    # Just one program
                    program = programs[0]
            
            # Find folder based on program name
            folder = folders.get(program)

            # Skip if folder not found (bad data?)
            if not folder:
                continue

            # Create Placemark
            p = etree.Element("Placemark")

            # Title
            title = etree.Element("name")
            title.text = r.Title.strip().decode('UTF-8')
            p.append(title)

            # Description - use br not p
            description_html = []
            description_el = etree.Element("description")

            if r.Description:
                description_html.append("<p><br />%s</p>" % r.Description.strip().decode('UTF-8'))

            if r.portal_type in ['Event']:
                style_url = etree.Element("styleUrl")
                style_url.text = "#style-%s" % self.normalize(program)
                p.append(style_url)

                datestamp = self.toLocalizedTime(r.start, end_time=r.end, long_format=1)
                description_html.append("""<p><br />
                                                <b>When:</b> %s<br />
                                                <b>Where:</b> %s
                                            </p>""" % (datestamp, r.short_location))

            description_html.append("""<p><br /><a href="%s">More Information</a>""" % r.getURL())

            description_el.text = "".join(description_html)
            p.append(description_el)

            # Create geographic coordinates
            point = etree.Element("Point")
            coords = etree.Element("coordinates")
            coords.text="%s,%s,0" % (info[4], info[3])
            point.append(coords)
            p.append(point)

            # Append Placemark to folder
            folder.append(p)

        # Append folders to document if they have contents and are the filtered
        # program (if provided)
        for k in sorted(folders.keys()):
            if self.filter_program and k != self.filter_program:
                continue
            folder = folders[k]
            if folder.find("Placemark"):
                d.append(folder)

        # Append document to KML object
        kml.append(d)

        # Get XML output
        xml = etree.tostring(kml, pretty_print=True, xml_declaration=True, encoding='UTF-8')

        # Set headers
        self.request.response.setHeader('Content-Type', 'application/vnd.google-earth.kmz')
        self.request.response.setHeader('Content-Disposition', 'attachment; filename="%s.kmz"' % self.context.getId())

        # ZIP XML
        sio = StringIO()
        zf = zipfile.ZipFile(sio, mode='w')
        zinfo = zipfile.ZipInfo("%s.kml" % self.context.getId())
        zinfo.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(zinfo, xml)
        zf.close()

        # Output zipped stream.
        return sio.getvalue()

class KMLAllView(KMLView):

    def __init__(self, context, request, show_all=True):
        self.context = context
        self.request = request
        self.show_all = show_all
        self.filter_program = None