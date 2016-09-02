import requests

# Call to external Plone system when content is set to import workflow state

# Configure hostname
HOSTNAME="cms.extension.psu.edu"

# Configure workflow name to import URL
workflow_to_import_url = {
    'z6_atlas-import-article' : "http://%s/@@import_article" % HOSTNAME,
    'z6_atlas-import-video' : "http://%s/@@import_video" % HOSTNAME,
}

def importContent(context, event):

    # Look up import URL based on event action
    import_url = workflow_to_import_url.get(event.action, None)

    # Return if we didn't find one
    if not import_url:
        return False

    # Get UID from item
    uid = context.UID()

    # POST data to Plone
    post_data = {'UID' : uid}
    response = requests.post(import_url, data=post_data)

    # Response, status etc
    response.text
    response.status_code

    if response.status_code == 200:
        data = response.json()

        if data.get('external_url', None):
            return True

    else:
        raise Exception('%d: %s' % (response.status_code, response.text))

    return False