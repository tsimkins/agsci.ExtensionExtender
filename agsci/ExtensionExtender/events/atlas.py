import requests

# Call to external Plone system when content is set to import workflow state

IMPORT_URL = "http://agplonesrv.ag.psu.edu/atlas-test/@@import_article"

def onArticleImport(context, event):

    if event.action in ['z6_atlas-import-article', ]:

        # Get UID from item        
        uid = context.UID()

        # POST data to Jitterbit
        post_data = {'UID' : uid}
        response = requests.post(IMPORT_URL, data=post_data)

        # Response, status etc
        response.text
        response.status_code
        
        if response.status_code == 200:
            data = response.json()

            if data.get('external_url', None):
                return True
    
    return False

