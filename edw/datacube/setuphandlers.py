""" Various setup
"""
import logging
logger = logging.getLogger('edw.datacube')
from Products.CMFCore.utils import getToolByName


def importVarious(self):
    """ Various setup
    """
    if self.readDataFile('edw.datacube.txt') is None:
        return

    site = self.getSite()
    st = getToolByName(site, "portal_setup")
    st.runAllImportStepsFromProfile("profile-Products.Ploneboard:default")
