from zope.interface import implements, Interface
from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from Acquisition import aq_acquire, aq_inner
from collective.contentleadimage.utils import getImageAndCaptionFieldNames
from DateTime import DateTime
from urllib import urlencode
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from BeautifulSoup import BeautifulSoup, NavigableString, Tag
from zope.component import getUtility, getMultiAdapter
from collective.contentleadimage.leadimageprefs import ILeadImagePrefsForm
from Products.agCommon.browser.views import FolderView, IFolderView
from urlparse import urljoin
from uuid import uuid1
import re

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, BaseDocTemplate, Frame, PageTemplate, FrameBreak
from reportlab.platypus.flowables import HRFlowable, KeepTogether, ImageAndFlowables, ParagraphAndImage
from reportlab.platypus.figures import ImageFigure as ImageFigureBase
from reportlab.platypus.figures import FlexFigure
from reportlab.platypus.tables import Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import Color, HexColor
from reportlab.rl_config import _FUZZ
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from io import BytesIO
from uuid import uuid4

from PIL import Image as PILImage

import os

try:
    from zope.app.component.hooks import getSite
except ImportError:
    from zope.component.hooks import getSite

from Products.CMFPlone.interfaces import IPloneSiteRoot

class ImageFigure(ImageFigureBase, Image):
    """Image with a caption below it"""
    def __init__(self, img_data, caption, width, height, background=None, align='right', max_image_width=None, column_count=1):
        self.img = PILImage.open(img_data)
        w, h = self.img.size

        if max_image_width > w:
            scaleFactor = max_image_width/w            
        else:
            scaleFactor = width/w            

        FlexFigure.__init__(self, w*scaleFactor, h*scaleFactor, caption, background)
        self.border=0
        self.captionFont='Helvetica'
        self.captionTextColor=HexColor('#717171')
        self.captionSize=9
        self.scaleFactor = self._scaleFactor = scaleFactor
        self.vAlign = 'TOP'
        self.hAlign = 'LEFT'
        self.column_count = column_count

    def drawFigure(self):
        (w,h) = self.img.size
        if self.column_count == 1:
            self.canv.drawInlineImage(self.img, x=-w*self.scaleFactor/2, y=0, width=w*self.scaleFactor, height=h*self.scaleFactor)
        else:
            self.canv.drawInlineImage(self.img, x=0, y=0, width=w*self.scaleFactor, height=h*self.scaleFactor)
            
    def drawCaption(self):
        (w,h) = self.img.size
        self.captionStyle.alignment = TA_LEFT

        if self.column_count == 1:
            self.captionPara.drawOn(self.canv, -w*self.scaleFactor/2, 0)  
        else:
            self.captionPara.drawOn(self.canv, 0, 0)  


    @property
    def drawWidth(self):
        return self.width

    @property
    def drawHeight(self):
        caption_height = self.captionPara.wrap(self.width, 100)[1] + self.captionGap
        return self.figureHeight + caption_height

    def _restrictSize(self,aW,aH):
        if self.drawWidth>aW+_FUZZ or self.drawHeight>aH+_FUZZ:   
            self._oldDrawSize = self.drawWidth, self.drawHeight 
            factor = min(float(aW)/self.drawWidth,float(aH)/self.drawHeight)
            self.drawWidth *= factor
            self.drawHeight *= factor
        return self.drawWidth, self.drawHeight

    def _unRestrictSize(self):
        dwh = getattr(self,'_oldDrawSize',None)
        if dwh:
            self.drawWidth, self.drawHeight = dwh




class FactsheetDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kw):
        BaseDocTemplate.__init__(self,filename, **kw)

    def registerTOC(self, flowable):
        text = flowable.getPlainText()
        style = flowable.style.name
        unique_key = uuid4().hex
        self.canv.showOutline()
        self.canv.bookmarkPage(unique_key)
        if style == 'Heading1':
            self.canv.addOutlineEntry(text, unique_key, level=0, closed=None)
        elif style == 'Heading2':
            self.canv.addOutlineEntry(text, unique_key, level=1, closed=None)
        elif style == 'Heading3':
            self.canv.addOutlineEntry(text, unique_key, level=2, closed=None)


    def afterFlowable(self, flowable):
        "Registers TOC entries."
        if isinstance(flowable, Paragraph):
            self.registerTOC(flowable)
        elif isinstance(flowable, ImageAndFlowables):
            for i in flowable._content:
                if isinstance(i, Paragraph):
                    self.registerTOC(i)

class FactsheetPDFView(FolderView):
    """
    View for downloading PDF version of factsheet
    """
    implements(IFolderView)

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.site = getSite()

    @property
    def portal_state(self):
        return getMultiAdapter((self.context, self.request), name=u'plone_portal_state')

    @property
    def anonymous(self):
        return self.portal_state.anonymous()

    def getFilename(self):

        # Use the publication code as the filename, if it exists.  Otherwise,
        # use the plone id

        filename = self.getPublicationCode()

        if not filename:
            filename = self.context.getId()
        
        return '%s.pdf' % filename

    def __call__(self):
    
        # If we're an anonymous user, and createPDF errors, send an email, and
        # return a boring and unhelpful error message.  If we're logged in, let
        # the error happen.
        
        if self.anonymous:
        
            try:
                pdf = self.createPDF()
            except:
                # Send email
                emailUsers = ['webservices@ag.psu.edu']
                mFrom = "do.not.reply@psu.edu"
                mSubj = "Error auto-generating PDF: %s" % self.context.Title()
                mMsg = '<p><strong>ERROR:</strong> <a href="%s">%s</a></p>'  % (self.context.absolute_url(), self.context.Title())
                mailHost = self.context.MailHost
        
                for mTo in emailUsers:
                    mailHost.secureSend(mMsg.encode('utf-8'), mto=mTo, mfrom=mFrom, subject=mSubj, subtype='html')
    
                # Return error message
                return "<h1>Error</h1><p>Sorry, an error has occurred.</p>"
                
        else:

            pdf = self.createPDF()


        self.request.response.setHeader('Content-Type', 'application/pdf')
        self.request.response.setHeader('Content-Disposition', 'attachment; filename="%s"' % self.getFilename())

        return pdf

    def getPublicationCode(self):
        if hasattr(self.context, 'extension_publication_code') and self.context.extension_publication_code:
            return self.context.extension_publication_code.upper().strip()
        else:
            return ""


    def getPublicationSeries(self):
        if hasattr(self.context, 'extension_publication_series') and self.context.extension_publication_series:
            return self.context.extension_publication_series.strip()
        else:
            return ""

    def createPDF(self):

        # -------------------------------------------------------------------------
        # Define functions used internally
        # -------------------------------------------------------------------------

        # Returns the plain (non-HTML) text for an item.  Used at the lowest level
        # of the DOM tree because it doesn't preserve any HTML formatting

        def getItemText(item):
            if isinstance(item, Tag):
                return portal_transforms.convert('html_to_text', repr(item)).getData()
            elif isinstance(item, NavigableString):
                return str(item).strip()
            else:
                return str(item).strip()


        # Provides the limited subset of HTML content used by the PDF generator
        space_before_punctuation_re = re.compile(u"\s+([.;:,!?])", re.I|re.M)

        def getInlineContents(item):
            p_contents = []
            for i in item.contents:
                if isinstance(i, Tag):
                    item_type = i.name
                    if item_type in ['b', 'strong', 'i', 'em', 'super', 'sub', 'a']:
                        for a in ['class', 'title', 'rel']:
                            if i.get(a):
                                del i[a]
                        if item_type == 'strong':
                            i.name = 'b'
                        elif item_type == 'em':
                            i.name = 'i'
                        elif item_type == 'a':
                            i.name = 'link'
                            if not (i['href'].startswith('http') or i['href'].startswith('mailto')):
                                i['href'] = urljoin(self.context.absolute_url(), i['href'])
                            # Wouldn't it be nice to underline the links?
                            i['color'] = 'blue'
                        if i.string:
                            p_contents.append(repr(i))
                        else:
                            p_contents.append(getInlineContents(i))
                    else:
                        p_contents.append(getItemText(i))
                elif isinstance(i, NavigableString):
                    p_contents.append(str(i).strip())

            contents = " ".join(p_contents)
            return space_before_punctuation_re.sub(r"\1", contents)

        # Returns structure containing table data when passed a BeautifulSoup
        # <table> element.
        def getTableData(item):

            def getCellSpan(cell):
                colspan = int(cell.get('colspan', 1))
                rowspan  = int(cell.get('rowspan', 1))
                return (colspan, rowspan)

            th_bg = HexColor('#CCCCCC')
            th_text = HexColor('#000000')
            grid = HexColor('#999999')

            table_data = []
            table_style = []

            r_index = 0

            for tr in item.findAll('tr'):
                c_index = 0

                table_row = []

                for i in tr.findAll('th'):
                    table_row.append(Paragraph(getInlineContents(i), th_cell))
                    (colspan, rowspan) = getCellSpan(i)
                    c_max = c_index + colspan - 1
                    r_max = r_index + rowspan - 1
                    table_style.extend([
                        ('FONTNAME', (c_index,r_index), (c_index,r_index), 'Times-Bold'),
                        ('FONTSIZE', (c_index,r_index), (c_index,r_index), 9),
                        ('BACKGROUND', (c_index,r_index), (c_index,r_index), th_bg),
                        ('GRID', (c_index,r_index), (c_max,r_max), 0.5, grid),
                        ('TEXTCOLOR', (c_index,r_index), (c_index,r_index), th_text),
                        ('LEFTPADDING', (c_index,r_index), (c_index,r_index), 3),
                        ('RIGHTPADDING', (c_index,r_index), (c_index,r_index), 3),
                        ('SPAN', (c_index,r_index), (c_max,r_max)),
                      ]
                    )
                    c_index = c_index + 1

                for i in tr.findAll('td'):

                    td_align = i.get('align', 'LEFT').upper()

                    if td_align == 'RIGHT':
                        p = Paragraph(getInlineContents(i), td_cell_right)
                    else:
                        p = Paragraph(getInlineContents(i), td_cell)

                    p.hAlign = td_align

                    table_row.append(p)
                   
                    (colspan, rowspan) = getCellSpan(i)
                    c_max = c_index + colspan - 1
                    r_max = r_index + rowspan - 1

                    table_style.extend([
                        ('GRID', (c_index,r_index), (c_max,r_max), 0.5, grid),
                        ('FONTNAME', (c_index,r_index), (c_index,r_index), 'Times-Roman'),
                        ('FONTSIZE', (c_index,r_index), (c_index,r_index), 9),
                        ('LEFTPADDING', (c_index,r_index), (c_index,r_index), 3),
                        ('RIGHTPADDING', (c_index,r_index), (c_index,r_index), 3),
                        ('SPAN', (c_index,r_index), (c_max,r_max)),
                        ('ALIGN', (c_index,r_index), (c_index,r_index), td_align),
                      ]
                    )

                    c_index = c_index + 1

                table_data.append(table_row)
                r_index = r_index + 1

            caption = item.find('caption')

            return (table_data, TableStyle(table_style), caption)


        # Provides the PDF entities for the corresponding HTML tags.

        def getContent(item, bump_headings=False):
            pdf = []
            if isinstance(item, Tag):
                className=item.get('class', '').split()
                item_type = item.name
                if item_type in ['h2', 'h3', 'h4', 'h5', 'h6']:
                    item_style = tag_to_style.get(item_type)
                    h = Paragraph(getItemText(item), styles[item_style])
                    h.keepWithNext = True
                    pdf.append(h)
                    if item_type == 'h2' and not bump_headings:
                        hr = HRFlowable(width='100%', thickness=0.25, spaceBefore=2, spaceAfter=4, color=styles[item_style].textColor)
                        hr.keepWithNext = True
                        pdf.append(hr)
                elif item_type in ['table']:
                    (table_data, table_style, caption) = getTableData(item)
                    table = Table(table_data)
                    table.setStyle(table_style)
                    table.hAlign = 'LEFT'
                    table.spaceBefore = 10
                    table.spaceAfter = 10

                    if caption:
                        caption_el = Paragraph(getInlineContents(caption), discreet)
                        pdf.append(KeepTogether([table, caption_el]))
                    else:
                        pdf.append(table)

                elif item_type in ['ul']:
                    for i in item.findAll('li'):
                        pdf.append(Paragraph('<bullet>&bull;</bullet>%s' % getInlineContents(i), bullet_list))
                elif item_type in ['ol']:
                    # Sequences were incrementing based on previous PDF generations.
                    # Including explicit ID and reset
                    li_uuid = uuid1().hex
                    for i in item.findAll('li'):
                        pdf.append(Paragraph('<seq id="%s" />. %s' % (li_uuid, getInlineContents(i)), bullet_list))
                    pdf.append(Paragraph('<seqReset id="%s" />' % li_uuid, styles['Normal']))
                elif item_type in ['p'] or (item_type in ['div'] and 'captionedImage' in className or 'callout' in className or 'pullquote' in className):

                    has_image = False

                    # Pull images out of items and add before
                    for img in item.findAll('img'):
                        img.extract()
                        src = img['src'].replace(self.site.absolute_url(), '')

                        if src.startswith('/'):
                            src = src.replace('/', '', 1)
                            
                        try:
                            img_obj = self.site.restrictedTraverse(str(src))
                        except KeyError:
                            continue

                        has_image = True
                        pdf_image = getImage(img_obj)
                        pdf.append(pdf_image)

                    # If we had an image, and the next paragraph has the
                    # 'discreet' class (is a caption) then keep them together
                    if has_image:
                        s = item.findNextSiblings()
                        if s and 'discreet' in s[0].get('class', ''):
                            pdf[-1].keepWithNext = True

                    # Get paragraph contents
                    p_contents = getInlineContents(item)

                    # Don't add anything if no contents.
                    if not p_contents:
                        pass
                    elif 'callout' in className or 'pullquote' in className:
                        pdf.append(Paragraph(p_contents, callout))
                    elif 'discreet' in className or 'captionedImage' in className:
                        if len(pdf) and isinstance(pdf[-1], Image):
                            pdf[-1].keepWithNext = True
                        pdf.append(Paragraph(p_contents, discreet))
                    else:
                        pdf.append(Paragraph(p_contents, styles["Normal"]))

                elif item_type in ['div']:
                    for i in item.contents:
                        pdf.extend(getContent(i))

                elif item_type == 'blockquote':
                    pdf.append(Paragraph(getItemText(item), blockquote))
                else:
                    pdf.append(Paragraph(getItemText(item), styles["Normal"]))
            elif isinstance(item, NavigableString):
                if item.strip():
                    pdf.append(Paragraph(item, styles["Normal"]))
            return pdf

        # -------------------------------------------------------------------------
        # Main body of create PDF
        # -------------------------------------------------------------------------

        # Get document attributes

        title = self.context.Title()
        desc = self.context.Description()
        text = self.context.getText()

        # Number of columns
        column_count = 2

        if hasattr(self.context, 'extension_publication_column_count'):
            column_count = getattr(self.context, 'extension_publication_column_count', '2')

        try:
            column_count = int(column_count)
        except:
            column_count = 2

        # Grab the publication code
        publication_code = self.getPublicationCode()

        # Grab the publication series
        publication_series = self.getPublicationSeries()

        # Clean up text
        text = text.replace('&nbsp;', ' ')

        # Colors - Maybe have presets?
        #header_rgb = (0.42,0.56,0.07)
        #header_rgb = (0.12,0.18,0.30) # Blue
        #header_rgb = (0.33,0.57,0.31) # Green (too light)
        header_rgb = HexColor('#4B7D45') # Green (dark enough)
        
        # Callout Colors
        callout_background_rgb = HexColor('#F6F6F6')

        # Styles

        styles=getSampleStyleSheet()

        styles['Normal'].spaceBefore = 3
        styles['Normal'].spaceAfter = 6
        styles['Normal'].fontName = 'Times-Roman'

        # Series Heading
        styles.add(ParagraphStyle('SeriesHeading'))
        styles['SeriesHeading'].spaceBefore = 0
        styles['SeriesHeading'].spaceAfter = 2
        styles['SeriesHeading'].fontSize = 10
        styles['SeriesHeading'].textColor = (0,0,0)
        styles['SeriesHeading'].leading = 13
        styles['SeriesHeading'].fontName = 'Helvetica-Bold'
        styles['SeriesHeading'].textTransform = 'uppercase'
        
        styles['Heading1'].fontSize = 25
        styles['Heading1'].fontName = 'Helvetica-Bold'
        styles['Heading1'].leading = 29
        styles['Heading1'].spaceBefore = 2
        styles['Heading1'].spaceAfter = 12
        styles['Heading1'].textColor = header_rgb     

        styles['Heading2'].allowWidows = 0
        styles['Heading2'].fontName = 'Helvetica-Bold'
        styles['Heading2'].fontSize = 15
        styles['Heading2'].leading = 18
        styles['Heading2'].spaceAfter = 8
        styles['Heading2'].spaceAfter = 2
        styles['Heading2'].textColor = header_rgb
        
        styles['Heading3'].allowWidows = 0
        styles['Heading3'].fontName = 'Helvetica-Bold'
        styles['Heading3'].fontSize = 12
        styles['Heading3'].leading = 14
        styles['Heading3'].spaceAfter = 4
        styles['Heading3'].textColor = header_rgb
                
        styles['Heading4'].allowWidows = 0
        styles['Heading4'].fontName = 'Helvetica-Bold'
        styles['Heading4'].fontSize = 10
        styles['Heading4'].leading = 12
        styles['Heading4'].spaceAfter = 6
        styles['Heading4'].textColor = header_rgb
        
        th_cell = ParagraphStyle('TableHeading')
        th_cell.spaceBefore = 3
        th_cell.spaceAfter = 6
        th_cell.fontSize = 10
        th_cell.fontName = 'Times-Bold'

        td_cell = ParagraphStyle('TableData')
        td_cell.spaceBefore = 3
        td_cell.spaceAfter = 6
        td_cell.fontSize = 10
        td_cell.fontName = 'Times-Roman'

        td_cell_right = ParagraphStyle('TableDataRight')
        td_cell_right.spaceBefore = 3
        td_cell_right.spaceAfter = 6
        td_cell_right.fontSize = 10
        td_cell_right.fontName = 'Times-Roman'
        td_cell_right.alignment = TA_RIGHT

        bullet_list = ParagraphStyle('BulletList')
        bullet_list.spaceBefore = 4
        bullet_list.spaceAfter = 4
        bullet_list.fontName = 'Times-Roman'
        bullet_list.bulletIndent = 5
        bullet_list.leftIndent = 17
        bullet_list.bulletFontSize = 12

        blockquote = ParagraphStyle('Blockquote')
        blockquote.leftIndent = 12
        blockquote.rightIndent = 8
        blockquote.spaceAfter = 6
        blockquote.fontName = 'Times-Roman'

        discreet = ParagraphStyle('Discreet')
        discreet.fontSize = 9
        discreet.textColor = HexColor('#717171')
        discreet.spaceAfter = 12
        discreet.spaceBefore = 1

        callout = ParagraphStyle('Callout')
        callout.fontSize = 10
        callout.textColor = header_rgb
        callout.spaceAfter = 20
        callout.spaceBefore = 22
        callout.backColor = callout_background_rgb
        callout.borderColor = header_rgb
        callout.borderWidth = 1
        callout.borderPadding = (8, 12, 10, 12)
        callout.rightIndent = 15
        callout.leftIndent = 15

        statement = ParagraphStyle('Statement')
        statement.fontSize = 8
        statement.fontName = 'Times-Roman'
        statement.spaceAfter = 5
        statement.leading = 10

        description = ParagraphStyle('Description')
        description.spaceBefore = 6
        description.spaceAfter = 8
        description.fontSize = 11
        description.fontName = 'Helvetica-Bold'
        description.leading = 13

        padded_image = ParagraphStyle('PaddedImage')
        padded_image.spaceBefore = 12
        padded_image.spaceAfter = 12

        single_line = ParagraphStyle('SingleLine')
        single_line.fontSize = 9
        single_line.fontName = 'Times-Roman'
        single_line.spaceBefore = 0
        single_line.spaceAfter = 0

        single_line_cr = ParagraphStyle('SingleLineCR')
        single_line_cr.fontSize = 9
        single_line_cr.fontName = 'Times-Roman'
        single_line_cr.spaceBefore = 0
        single_line_cr.spaceAfter = 10

        # Create document
        pdf_file = BytesIO()
        margin = 36

        # Debug for formatting boundary
        showBoundary=0

        doc = FactsheetDocTemplate(pdf_file,pagesize=letter, title=title,
                                   rightMargin=margin,leftMargin=margin, showBoundary=showBoundary,
                                   topMargin=margin,bottomMargin=margin)

        # Standard padding for document elements
        element_padding = 6
        
        # Document image setttings
        max_image_width = doc.width/column_count-(3*element_padding)
        
        if column_count <= 1:
            max_image_width = doc.width/2-(3*element_padding)

        # Returns a reportlab image object based on a Plone image object

        def getImage(img_obj, scale=True, reader=False, width=max_image_width, style="", column_count=column_count, caption="", leadImage=False, hAlign=None, body_image=True):

            if not leadImage and body_image and column_count == 1:
                # Special case to make one column body images 66% of the page
                width = 1.33*width

            img_width = img_obj.width
            img_height = img_obj.height

            if scale and (img_width > width):
                img_height = (width/img_width)*img_height
                img_width = width

            if hasattr(img_obj, 'data'):
                if hasattr(img_obj.data, 'data'):
                    img_data = BytesIO(img_obj.data.data)
                else:
                    img_data = BytesIO(img_obj.data)
            elif hasattr(img_obj, '_data'):
                img_data = BytesIO(img_obj._data)
            else:
                img_data = BytesIO('')

            if reader:
                img = ImageReader(img_data)
            else:
                if caption or leadImage:
                    img = ImageFigure(img_data, caption=caption, width=img_width, height=img_height, align="right", max_image_width=width, column_count=column_count)
                else:
                    img = Image(img_data, width=img_width, height=img_height)

            if style:
                img.style = style

            if hAlign:
                img.hAlign = hAlign
            elif column_count == 1:
                img.hAlign = TA_LEFT
            else:
                img.hAlign = TA_CENTER

            return img

        #-------------- calculated coordinates/w/h

        extension_url_image = self.site.portal_skins.agcommon_images['extension-url.png']
        extension_url_image_width = 0.5*max_image_width

        # Factsheet title 
        title_lines = 3
        publication_series_height = 0
                
        if publication_series:
            # If series heading, only 2 title lines
            title_lines = 2

            # One line for the series heading
            publication_series_height = styles['SeriesHeading'].spaceBefore + \
                                        styles['SeriesHeading'].spaceAfter + \
                                        styles['SeriesHeading'].leading 

        title_height = styles['Heading1'].spaceBefore + \
                       styles['Heading1'].spaceAfter + \
                       (title_lines * styles['Heading1'].leading) + \
                       publication_series_height + element_padding


        # Penn State/Extension Footer Image
        footer_image_width = 222.0 # 72 points/inch * 3.125"
        footer_image = self.site.portal_skins.agcommon_images['extension-factsheet-footer.png']
        footer_image_height = footer_image_width*(1.0*footer_image.height/footer_image.width)

        # Header and footer on first page
        def header_footer(canvas,doc):
            canvas.saveState()

            # Line under Title
            canvas.setStrokeColorRGB(0,0,0)
            line_y=doc.bottomMargin+doc.height-title_height
            canvas.line(doc.leftMargin+element_padding, line_y, doc.width+doc.leftMargin-element_padding, line_y)

            # Footer
            canvas.drawImage(getImage(footer_image, scale=False, reader=True), doc.leftMargin+element_padding, 72.0/2, width=footer_image_width, height=footer_image_height, preserveAspectRatio=True, mask='auto')

            canvas.restoreState()

        # Footer for pages 2 and after
        def footer(canvas,doc):
            canvas.saveState()
            canvas.setFont('Times-Roman',9)
            canvas.drawString(margin, 24, "Page %d" % doc.page)
            canvas.setFont('Times-Roman',9)
            canvas.drawRightString(doc.width+margin+element_padding, 24, title)
            canvas.restoreState()

        #Two Columns For First (title) page

        title_y = doc.bottomMargin + doc.height - title_height        

        title_column_y = doc.bottomMargin+footer_image_height+element_padding

        title_column_height = title_y - title_column_y

        title_frame_title = Frame(doc.leftMargin, title_y, doc.width, title_height, id='title_title', showBoundary=showBoundary)

        title_frames = [title_frame_title]

        for i in range(0,column_count):
            lm = doc.leftMargin + i * (doc.width/column_count+element_padding)
            w = doc.width/column_count-element_padding
            title_frame = Frame(lm, title_column_y, w, title_column_height, id='title_col%d' % i, showBoundary=showBoundary)
            title_frames.append(title_frame)

        #Two Columns For remaining page

        other_frames = []

        for i in range(0,column_count):
            lm = doc.leftMargin + i * (doc.width/column_count+element_padding)
            w = doc.width/column_count-element_padding
            other_frame = Frame(lm, doc.bottomMargin, w, doc.height, id='other_col%d' % i, showBoundary=showBoundary)
            other_frames.append(other_frame)

        title_template = PageTemplate(id="title_template", frames=title_frames,onPage=header_footer)
        other_template = PageTemplate(id="other_template", frames=other_frames,onPage=footer)

        doc.addPageTemplates([title_template,other_template])
        doc.handle_nextPageTemplate("other_template")

        # ---------------------------------------------------------------------
        # Convert HTML to PDF (Magic goes here)
        # ---------------------------------------------------------------------

        # Soupify
        soup = BeautifulSoup(text)

        # This list holds the PDF elements
        pdf = []

        # Series, page heading and description in top frame, then framebreak
        # into two columns.  Optionally add the description to the body if the
        # flag is set.

        if publication_series:
            pdf.append(Paragraph(publication_series, styles['SeriesHeading']))

        pdf.append(Paragraph(title, styles["Heading1"]))

        # Move to next frame
        pdf.append(FrameBreak())

        if description:
            pdf.append(Paragraph(desc, description))

        # If we're a news item, append the date
        if self.context.portal_type in ['News Item']:
            pdf.append(Paragraph('Posted: %s' % self.context.getEffectiveDate().strftime('%B %d, %Y'), discreet))            

        # Lead Image and caption as first elements. Not doing News Item image.
        (IMAGE_FIELD_NAME, IMAGE_CAPTION_FIELD_NAME) = getImageAndCaptionFieldNames(self.context)
        leadImage_field = self.context.getField(IMAGE_FIELD_NAME)
        leadImage_caption_field = self.context.getField(IMAGE_CAPTION_FIELD_NAME)

        show_leadimage = getattr(self.context, 'show_leadimage_context', True)

        if show_leadimage and leadImage_field and leadImage_caption_field:
            leadImage = leadImage_field.get(self.context)
            leadImage_caption = leadImage_caption_field.get(self.context)
            if leadImage and leadImage.get_size():
                if column_count == 1:
                    pdf.append(getImage(leadImage, caption=leadImage_caption, leadImage=True))

                else:
                    pdf.append(getImage(leadImage)) 

                    if leadImage_caption: 
                        pdf.append(Paragraph(leadImage_caption, discreet)) 


        # portal_transforms will let us convert HTML into plain text
        portal_transforms = getToolByName(self.context, 'portal_transforms')

        # Equivalent PDF paragraph styles for HTML
        tag_to_style = {
            'h2' : 'Heading2',
            'h3' : 'Heading3',
            'h4' : 'Heading4',
            'h5' : 'Heading5',
            'h6' : 'Heading6',
            'p' : 'Normal'
        }

        # Push headings to the smallest level

        # If we have an h2, but not an h3 or h4, bump the heading styles down.

        attrs = ['allowWidows', 'fontName', 'fontSize', 'leading', 'spaceAfter', 'textColor', ]

        bump_headings = False

        if '<h2' in text and not '<h3' in text and not '<h4' in text:

            bump_headings = True
        
            heading_tags = sorted([x for x in tag_to_style.keys() if x.startswith('h')])

            for i in range(0, len(heading_tags) - 1):
                from_style = tag_to_style[heading_tags[i]]
                to_style = tag_to_style[heading_tags[i+1]]
                for a in attrs:
                    styles[from_style].__dict__[a] = styles[to_style].__dict__[a]



        # Loop through Soup contents
        for item in soup.contents:
            pdf.extend(getContent(item, bump_headings=bump_headings))

        # Embed lead images in paragraphs if we're a single column
        if column_count == 1:
            for i in range(1,len(pdf)-1):
                if isinstance(pdf[i], ImageFigureBase):

                    paragraphs = []
                    
                    for j in range(i+1, len(pdf)-1):
                        if isinstance(pdf[j], Paragraph) or isinstance(pdf[j], HRFlowable):
                            paragraphs.append(pdf[j])
                            pdf[j] = None
                        else:
                            break

                    if paragraphs:

                        pdf[i].hAlign="RIGHT"
                        
                        img_paragraph = ImageAndFlowables(pdf[i], paragraphs,imageLeftPadding=element_padding)

                        pdf[i] = img_paragraph

            while None in pdf:
                pdf.remove(None)

        # Contributors (as Contact Information) %%%
        contributors_viewlet = getMultiAdapter((self.context, self.request, self), name='agcommon.contributors')
        
        contributors_people = contributors_viewlet.people
        
        if contributors_people:
            # Adding h2 this way so as to take advantage of the underline and the
            # bump_headings parameter
            heading = Tag(BeautifulSoup(), 'h2')
            heading.insert(0, 'Contact Information')
            pdf.extend(getContent(heading, bump_headings=bump_headings))
            
            for person in contributors_viewlet.people:
                if person.get('url'):
                    person_name = Paragraph("""<b><a color="blue" href="%(url)s">%(name)s</a></b>""" % person, single_line)
                else:
                    person_name = Paragraph("""<b>%(name)s</b>""" % person, single_line)

                person_name.keepWithNext = True
                
                person_title = Paragraph("""%(title)s""" % person, single_line)
                person_title.keepWithNext = True
                
                person_email = Paragraph("""<a color="blue" href="mailto:%(email)s">%(email)s</a>""" % person, single_line)
                person_email.keepWithNext = True
                                
                person_phone = Paragraph("""%(phone)s""" % person, single_line_cr)

                pdf.append(person_name)
                pdf.append(person_title)
                pdf.append(person_email)
                pdf.append(person_phone)

        # All done with contents, appending line and statement
        pdf.append(HRFlowable(width='100%', spaceBefore=4, spaceAfter=4))                

        # Extension logo

        pdf.append(getImage(extension_url_image, scale=True, width=extension_url_image_width, style=padded_image, hAlign='LEFT', body_image=False))

        # Choose which statement
        aa_statement = """Penn State is an equal opportunity, affirmative action employer, and is committed to providing employment opportunities to all qualified applicants without regard to race, color, religion, age, sex, sexual orientation, gender identity, national origin, disability or protected veteran status."""
        
        statement_text = ("""Penn State College of Agricultural Sciences research and extension programs are funded in part by Pennsylvania counties, the Commonwealth of Pennsylvania, and the U.S. Department of Agriculture.

        Where trade names appear, no discrimination is intended, and no endorsement by Penn State Extension is implied.

        <b>This publication is available in alternative media on request.</b>

        %s

        &copy The Pennsylvania State University %d

        """ % (aa_statement, DateTime().year())).split("\n")

        # Append the publication code, if it exists
        if publication_code:
            statement_text.append("Code: %s" % publication_code)

        # Create paragraphs from the statement text
        for s in statement_text:
            if s.strip():
                pdf.append(Paragraph(s, statement))

        # Create PDF - multibuild instead of build for table of contents
        # functionality

        doc.multiBuild(pdf)
        #doc.build(pdf)

        # Pull PDF binary bits into variable, close file handle and return
        pdf_value = pdf_file.getvalue()
        pdf_file.close()
        return pdf_value
