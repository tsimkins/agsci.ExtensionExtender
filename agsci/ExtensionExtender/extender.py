from Products.Archetypes.public import LinesField, InAndOutWidget, StringField, StringWidget, LinesWidget, BooleanField, BooleanWidget, FileWidget, SelectionWidget, MultiSelectionWidget
from Products.FacultyStaffDirectory.interfaces.person import IPerson
from archetypes.schemaextender.field import ExtensionField
from archetypes.schemaextender.interfaces import ISchemaExtender, ISchemaModifier, IBrowserLayerAwareExtender
from interfaces import IExtensionExtenderLayer, IExtensionExtender, IExtensionCountiesExtender, IExtensionCourseExtender
from zope.component import adapts
from zope.interface import implements
from Products.Archetypes.utils import DisplayList
from Products.CMFCore.utils import getToolByName
from Acquisition import aq_acquire, aq_chain
from Products.CMFCore.interfaces import ISiteRoot
from plone.app.blob.field import BlobField
from Products.ATContentTypes.interfaces.event import IATEvent
from Products.ATContentTypes.interfaces.interfaces import IATContentType
from agsci.UniversalExtender.extender import ContentPublicationExtender, FilePublicationExtender

class _ExtensionStringField(ExtensionField, StringField): pass
class _ExtensionBooleanField(ExtensionField, BooleanField): pass
class _ExtensionBlobField(ExtensionField, BlobField): pass


class _ExtensionLinesField(ExtensionField, LinesField):

    def getDefault(self, instance, **kwargs):
        # Shortcut this field when creating non News Item/Events.  Specifically,
        # This prevents the lookup when creating folders.

        if instance.portal_type not in ['News Item', 'Event']:
            return ()

        for i in aq_chain(instance):
            if ISiteRoot.providedBy(i):
                break
            else:
                try:
                    v = self.get(i)
                    
                    if v:
                        return v
                except:
                    break

        return ()

    def get(self, instance, **kwargs):     
        __traceback_info__ = (self.getName(), instance, kwargs)
        try:
            kwargs['field'] = self
            return self.getStorage(instance).get(self.getName(), instance, **kwargs)
        except AttributeError:  
            return ()


class _DepartmentsField(_ExtensionLinesField):

    def Vocabulary(self, content_instance):

        return DisplayList(
            [
                ('abe', 'Agricultural and Biological Engineering'),
                ('aese', 'Agricultural Economics, Sociology, and Education'),
                ('animalscience', 'Animal Science'),
                ('ecosystems', 'Ecosystem Science and Management'),
                ('ento', 'Entomology'),
                ('foodscience', 'Food Science'),
                ('plantpath', 'Plant Pathology and Environmental Microbiology'),
                ('plantscience', 'Plant Science'),
                ('vbs', 'Veterinary and Biomedical Sciences' ),
            ]
        )

class _TopicsField(_ExtensionLinesField):

    def Vocabulary(self, content_instance):

        ptool = getToolByName(content_instance, 'portal_properties')
        props = ptool.get("extension_properties")

        if props and props.extension_topics:
            return DisplayList([(x.strip(), x.strip()) for x in sorted(props.extension_topics)])
        else:
            return DisplayList([('N/A', 'N/A')])

class _SubtopicsField(_ExtensionLinesField):

    def Vocabulary(self, content_instance):

        ptool = getToolByName(content_instance, 'portal_properties')
        props = ptool.get("extension_properties")

        if props and props.extension_subtopics:
            return DisplayList([(x.strip(), x.strip()) for x in sorted(props.extension_subtopics)])
        else:
            return DisplayList([('N/A', 'N/A')])

class _CountiesField(_ExtensionLinesField):

    def getCounties(self, content_instance):
        ptool = getToolByName(content_instance, 'portal_properties')
        props = ptool.get("extension_properties")

        if props and props.extension_counties:
            return [(x.strip(), x.strip()) for x in sorted(props.extension_counties)]
        else:
            return [('N/A', 'N/A')]

    def Vocabulary(self, content_instance):
        return DisplayList(self.getCounties(content_instance))

class _EventCountiesField(_CountiesField):

    def Vocabulary(self, content_instance):

        counties = self.getCounties(content_instance)

        if len(counties) > 1:
            counties.insert(0, ('N/A', 'N/A'))

        return DisplayList(counties)

class _CoursesField(_ExtensionLinesField):

    def Vocabulary(self, content_instance):

        extension_courses_tool = getToolByName(content_instance, 'extension_course_tool')

        if extension_courses_tool:
            courses = [('', 'Select a course...'),]
            courses.extend([(x.strip(), x.strip()) for x in extension_courses_tool.getCourses()])
            return DisplayList(courses)
        else:
            return DisplayList([('N/A', 'N/A')])
            

class FSDExtensionExtender(object):
    adapts(IPerson)
    implements(ISchemaExtender, IBrowserLayerAwareExtender, ISchemaModifier)

    layer = IExtensionExtenderLayer
    
    fields = [
        _CountiesField(
            "extension_counties",
                schemata="Professional Information",
                required=False,
                searchable=True,
                widget = InAndOutWidget(
                    label=u"Counties",
                    description=u"Counties that this person is associated with",
                    condition="python:member.has_role('Manager', object) or member.has_role('Personnel Manager', object)",
            ),
        ),

        _TopicsField(
            "extension_topics",
                schemata="Professional Information",
                required=False,
                searchable=True,
                widget = InAndOutWidget(
                    label=u"Programs",
                    description=u"Extension programs that this item is associated with",
                    condition="python:member.has_role('Manager', object) or member.has_role('Personnel Manager', object)",
            ),
        ),

        _SubtopicsField(
            "extension_subtopics",
                schemata="Professional Information",
                required=False,
                searchable=True,
                widget = InAndOutWidget(
                    label=u"Topics",
                    description=u"Topics within the program(s) that this item is associated with",
                    condition="python:member.has_role('Manager', object) or member.has_role('Personnel Manager', object)",
            ),
        ),
        
        _ExtensionLinesField(
            "extension_areas",
                schemata="Professional Information",
                required=False,
                searchable=True,
                widget = LinesWidget(
                    label=u"Areas of Expertise",
                    description=u"One per line",
            ),
        ),

    ]

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields

class ExtensionExtender(object):
    adapts(IExtensionExtender)
    implements(ISchemaExtender, IBrowserLayerAwareExtender)

    layer = IExtensionExtenderLayer
    
    @property
    def fields(self):
        fields = []
        fields.extend(self.program_fields)
        fields.extend(self.counties_field)
        return fields

    @property
    def counties_field(self):
        return [
            _CountiesField(
                "extension_counties",
                    schemata="categorization",
                    required=False,
                    searchable=True,
                    widget = InAndOutWidget(
                    label=u"Counties",
                    description=u"Counties that this item is associated with",
                ),
            ),
        ]

    @property
    def program_fields(self):
        return [
            _TopicsField(
                "extension_topics",
                    schemata="categorization",
                    required=False,
                    searchable=True,
                    widget = InAndOutWidget(
                    label=u"Programs",
                    description=u"Extension programs that this item is associated with",
                ),
            ),
            _SubtopicsField(
                "extension_subtopics",
                    schemata="categorization",
                    required=False,
                    searchable=True,
                    widget = InAndOutWidget(
                    label=u"Topics",
                    description=u"Topics within the program(s) that this item is associated with",
                ),
            ),
        ]    

    @property
    def publication_fields(self):
        return [
            _ExtensionStringField(
                "extension_publication_series",
                    schemata="Publication",
                    required=False,
                    searchable=True,
                    widget=StringWidget(
                        label=u"Publication Series",
                        description=u"Optional",
                    ),
            ),
            _ExtensionBooleanField(
                "extension_publication_listing",
                schemata="Publication",
                required=False,
                default=False,
                widget=BooleanWidget(
                    label=u"Include in Extension Publications listing?",
                    description=u"",
                    condition="python:member.has_role('Manager', object)",
                ),
            ),
            _ExtensionBooleanField(
                "extension_publication_contact_pdc",
                schemata="Publication",
                required=False,
                default=False,
                widget=BooleanWidget(
                    label=u"Contact PDC",
                    description=u"",
                    condition="python:member.has_role('Manager', object)",
                ),
            ),
            _ExtensionBooleanField(
                "extension_publication_for_sale",
                schemata="Publication",
                required=False,
                default=False,
                widget=BooleanWidget(
                    label=u"Publication For Sale",
                    description=u"",
                    condition="python:member.has_role('Manager', object)",
                ),
            ),
            _ExtensionStringField(
                "extension_publication_cost",
                    schemata="Publication",
                    required=False,
                    searchable=False,
                    widget=StringWidget(
                        label=u"Publication Cost",
                    condition="python:member.has_role('Manager', object)",
                    ),
            ),
            _DepartmentsField(
                "agsci_departments",
                    schemata="Publication",
                    required=False,
                    searchable=False,
                    widget = InAndOutWidget(
                    label=u"Departments",
                    description=u"Academic Departments that this item is associated with",
                    condition="python:member.has_role('Manager', object)",
                ),
            ),
            _ExtensionStringField(
                "extension_override_page_count",
                    schemata="Publication",
                    required=False,
                    searchable=False,
                    widget=StringWidget(
                        label=u"Override automatic page count",
                    condition="python:member.has_role('Manager', object)",
                    ),
            ),
        ]

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields


# Content publications (e.g. a page with a PDF/URL/Autogenerated PDF)
# have the code and plus assorted options
class ExtensionContentPublicationExtender(ContentPublicationExtender, ExtensionExtender):

    layer = IExtensionExtenderLayer

    @property
    def fields(self):
        fields = super(ExtensionContentPublicationExtender, self).fields
        fields.extend(self.publication_fields)
        # Custom Options
        fields.extend([
            _ExtensionBooleanField(
                "extension_publication_download",
                schemata="Publication",
                required=False,
                default=False,
                widget=BooleanWidget(
                    label=u"Automatically generate PDF",
                    description=u"Verify the formatting of this PDF after checking this box. You may have to tweak the content to obtain a nicely formatted PDF.",
                    condition="python:member.has_role('Manager', object)",
                ),
            ),
            
            _ExtensionStringField(
                "extension_publication_column_count",
                schemata="Publication",
                required=False,
                default='2',
                widget=SelectionWidget(
                    label=u"Number of columns in publication",
                    description=u"",
                    format='select',
                    condition="python:member.has_role('Manager', object)",
                ),
                vocabulary=([(str(x), str(x)) for x in range(1,4)]),
            ),
    
            _ExtensionStringField(
                "extension_publication_description_body",
                schemata="Publication",
                required=False,
                default=False,
                widget=BooleanWidget(
                    label=u"Show description in body rather than header.",
                    description=u"",
                    condition="python:member.has_role('Manager', object)",
                ),
            ),
        ])

        fields.extend(super(ExtensionContentPublicationExtender, self).program_fields)

        return fields

    def fiddle(self, schema):
        # Put Publication series after publication code
        schema.moveField('extension_publication_series', after='extension_publication_code')
        schema.moveField('extension_publication_listing', pos='bottom')
        schema.moveField('agsci_departments', pos='bottom')
        return schema
        

# Just for files
class ExtensionFilePublicationExtender(FilePublicationExtender, ExtensionExtender):

    layer = IExtensionExtenderLayer

    custom_fields = [
        _ExtensionStringField(
            "extension_publication_sample",
            schemata="Publication",
            required=False,
            default=False,
            widget=BooleanWidget(
                label=u"Sample File",
                description=u"This file is a sample of the full publication.",
                condition="python:member.has_role('Manager', object)",
            ),
        ),
    ]

    @property
    def fields(self):
        fields = super(ExtensionFilePublicationExtender, self).fields
        fields.extend(self.publication_fields)
        fields.extend(super(ExtensionFilePublicationExtender, self).program_fields)
        fields.extend(self.custom_fields)
        return fields

    def fiddle(self, schema):
        # Put Publication series after publication code
        schema.moveField('extension_publication_series', after='extension_publication_code')
        schema.moveField('extension_publication_listing', pos='bottom')
        schema.moveField('agsci_departments', pos='bottom')
        return schema

class ExtensionEventExtender(ExtensionExtender):
    adapts(IATEvent)

    layer = IExtensionExtenderLayer

    @property
    def fields(self):
        fields = [
            _EventCountiesField(
                "extension_counties",
                    schemata="categorization",
                    required=True,
                    searchable=True,
                    widget = MultiSelectionWidget(
                    label=u"County",
                    description=u"County in which this event occurs. Choose 'N/A' if this is a webinar or virtual event.",
                ),
            ),

            _CoursesField(
                "extension_courses",
                    required=False,
                    searchable=True,
                    widget = SelectionWidget(
                    label=u"Course",
                    description=u"Course that this event is associated with",
                    format='select'
                ),
            ),
            _ExtensionStringField(
                "zip_code",
                    required=True,
                    searchable=True,
                    widget=StringWidget(
                        label=u"ZIP Code",
                        description=u"5-digit ZIP Code for event location. For webinars and other virtual events, enter 00000.",
                    ),
            ),
        ]
        
        fields.extend(super(ExtensionEventExtender, self).program_fields)
        
        return fields
        

    def fiddle(self, schema):
        # Make "Location" mandatory
        schema['location'].required=True

        tmp_field = schema['extension_counties'].copy()
        tmp_field.schemata = 'default'
        schema['extension_counties'] = tmp_field

        # Put courses before location
        schema.moveField('extension_courses', after='description')
        schema.moveField('zip_code', after='endDate')
        schema.moveField('extension_counties', after='zip_code')
        return schema

# Add Counties to anything
class ExtensionCountiesExtender(ExtensionExtender):
    adapts(IExtensionCountiesExtender)

    layer = IExtensionExtenderLayer

    @property
    def fields(self):
        return super(ExtensionCountiesExtender, self).counties_field

# Add translation widgets to an object
class TranslationExtender(object):
    adapts(IATContentType)

    implements(ISchemaExtender, IBrowserLayerAwareExtender)

    layer = IExtensionExtenderLayer

    fields = [
        _ExtensionBooleanField(
            "provide_translation_widget",
            schemata="settings",
            required=False,
            default=False,
            widget=BooleanWidget(
                label=u"Provide translation widget",
                description=u"",
            ),
        ),
    ]

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields


# Add additional fields to course collections
class CourseExtender(object):
    adapts(IExtensionCourseExtender)

    implements(ISchemaExtender, IBrowserLayerAwareExtender)

    layer = IExtensionExtenderLayer

    fields = [
        _ExtensionStringField(
            "extension_course_single_event",
            required=False,
            default='normal',
            widget=SelectionWidget(
                label=u"Single Annual Event Course Options",
                description=u"Actions to take if there is only one annual event for this course.",
                format="radio",
            ),
            vocabulary=[
                    ('normal', 'No action'),
                    ('redirect', 'Redirect to event URL'),
                    ('alias', 'Display event details and registration information'),
            ],
        ),
    ]

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields