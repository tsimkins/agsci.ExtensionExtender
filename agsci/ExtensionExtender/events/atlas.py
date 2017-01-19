import requests
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException

# Call to external Plone system when content is set to import workflow state

# Configure hostname
HOSTNAME="cms.extension.psu.edu"

# Configure workflow name to import URL
workflow_to_import_url = {
    'z6_atlas-import-article' : "http://%s/@@import_article" % HOSTNAME,
    'z6_atlas-import-video' : "http://%s/@@import_video" % HOSTNAME,
}

def importContent(context, event):

    # Verify that the workflow event action is one for which we're going to
    # import the content
    if event.action not in workflow_to_import_url.keys():
        return False

    # Get the parent object
    parent = context.aq_parent

    # Get the portal_workflow tool, and find the review states for this object
    # and the parent object
    wftool = getToolByName(context, 'portal_workflow')

    # Check if the parent's workflow state indicates that it's imported already.
    # If it is, don't import this object.  If the parent has no workflow state,
    # this probably means it's a Plone site.
    try:
        parent_review_state = wftool.getInfoFor(parent, 'review_state')
    except WorkflowException:
        parent_review_state = None

    if parent_review_state in ['atlas-import-article', 'atlas-import-video']:
        return False

    # This pushes the content from the current site to the new site via the API
    callImportAPI(context, event)

    # If the import was successful, set the status of all child objects that
    # are in the Atlas Ready state to Imported

    # Find all Atlas Ready items inside this object
    portal_catalog = getToolByName(context, "portal_catalog")

    context_path = "/".join(context.getPhysicalPath())

    results = portal_catalog.searchResults({'review_state' : 'atlas-ready',
                                            'path' : context_path
                                            })

    # For those items, call the workflow action specified by the parent event
    for r in results:

        # Skip current object
        if r.UID == context.UID():
            continue

        o = r.getObject()

        try:
            wftool.doActionFor(o, event.action)
        except WorkflowException:
            continue
        else:
            o.reindexObject()
            o.reindexObjectSecurity()

def callImportAPI(context, event):

    # Look up import URL based on event action.  If the URL doesn't exist in
    # the dict, there's no import done on it.
    import_url = workflow_to_import_url.get(event.action, None)

    # Return if we didn't find one
    if not import_url:
        return False

    # Get UID from item
    uid = context.UID()

    # POST data to Plone
    post_data = {'UID' : uid}
    response = requests.post(import_url, data=post_data)

    # If we received a 200 (success) return
    if response.status_code == 200:

        # Grab the JSON data
        data = response.json()

        # If the import returned a 200, but doesn't have a value for the
        # 'plone_id' key, raise an exception. This is a basic sanit check.
        if not data.get('plone_id', None):
            raise Exception('Return from import indicates issue: %s' % repr(data))

    # Raise an exception if the return code is not 200
    else:
        raise Exception('%d: %s' % (response.status_code, response.text))