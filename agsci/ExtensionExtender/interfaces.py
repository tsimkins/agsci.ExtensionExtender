from zope.interface import Interface
from plone.theme.interfaces import IDefaultPloneLayer
from agsci.UniversalExtender.interfaces import IUniversalPublicationExtender

class IExtensionExtenderLayer(IDefaultPloneLayer):
    """A Layer Specific to StartingPoint"""

class IExtensionExtender(Interface):
    """ marker interface """
    
class IExtensionPublicationExtender(IUniversalPublicationExtender):
    """
        Marker interface to denote something as a "publication", which will add
        the necessary fields to it.
    """

class IExtensionCountiesExtender(Interface):
    """
        Marker interface which allows us to add counties to anything
    """

class IExtensionCourseExtender(Interface):
    """
        Marker interface which allows us to treat a collection as a course landing page.
    """