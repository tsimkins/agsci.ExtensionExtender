from Products.CMFCore.utils import getToolByName

def uninstall(portal):
    setup_tool = getToolByName(portal, 'portal_setup')
    setup_tool.runAllImportStepsFromProfile('profile-agsci.ExtensionExtender:uninstall')
    return "Ran all uninstall steps."
