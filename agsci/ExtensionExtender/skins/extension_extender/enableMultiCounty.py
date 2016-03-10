from agsci.ExtensionExtender import enableMultiCounty
from Products.agCommon import unprotectRequest

unprotectRequest(container.REQUEST)

request = container.REQUEST
response =  request.response

enableMultiCounty(context)

return context.REQUEST.RESPONSE.redirect("%s/edit" % context.absolute_url())
