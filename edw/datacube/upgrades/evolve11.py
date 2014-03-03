"""Add ploneboard and necessary discussions
"""
import logging
logger = logging.getLogger('edw.datacube')
from zope.component.hooks import getSite


def importVarious(context):
    """ Run all import steps from Products.Ploneboard profile
    """
    context.runAllImportStepsFromProfile("profile-Products.Ploneboard:default")


def evolve(context):
    """ Add the initial board and discussions for each datacube
    """
    site = getSite()
    cat = context.portal_catalog

    if not 'forum' in site.objectIds():
        site.invokeFactory('Ploneboard', 'forum')

    brains = cat.searchResults(portal_type="DataCube", Language="all")
