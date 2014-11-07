from zope.interface import implements, Interface
from Products.agCommon.browser.views.newsletter import NewsletterView

class IEventPrintRegistration(Interface):
    pass

class EventPrintRegistration(NewsletterView):
    implements(IEventPrintRegistration)
    pass