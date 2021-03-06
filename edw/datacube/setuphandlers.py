""" Various setup
"""
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFCore.utils import getToolByName
import logging
import zope.event
logger = logging.getLogger('edw.datacube')


def importVarious(self):
    """ Various setup
    """
    if self.readDataFile('edw.datacube.txt') is None:
        return

    site = self.getSite()
    st = getToolByName(site, "portal_setup")
    st.runAllImportStepsFromProfile("profile-Products.Ploneboard:default")
    add_board(site)


def add_board(context):
    """ Create the default discussion board
    """
    board = context.get('board')

    if not board:
        context.invokeFactory('Ploneboard', 'board')
        board = context.get('board')
        zope.event.notify(ObjectInitializedEvent(board))
        logger.info('Created discussion board: %s', board.absolute_url())
