from agsci.ExtensionExtender import getContactEmails, getExtensionConfig, getDefaultFormEmail

request = container.REQUEST
response =  request.response

emails = []

county = str(request.county).strip()

if county:
    config = getExtensionConfig(context)
    config['county'] = county
    emails = getContactEmails(context, **config)

if emails:
    return emails
else:
    return getDefaultFormEmail(context)

