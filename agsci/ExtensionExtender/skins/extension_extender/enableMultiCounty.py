from agsci.ExtensionExtender import enableMultiCounty

request = container.REQUEST
response =  request.response

enableMultiCounty(context)

return context.REQUEST.RESPONSE.redirect("%s/edit" % context.absolute_url())
