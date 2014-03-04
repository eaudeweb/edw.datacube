"""Add ploneboard and necessary discussions
"""
from Products.CMFCore.utils import getToolByName
from zope.component.hooks import getSite
import logging
import transaction
logger = logging.getLogger('edw.datacube')


def importVarious(context):
    """ Run all import steps from Products.Ploneboard profile
    """
    context.runAllImportStepsFromProfile("profile-Products.Ploneboard:default")


def evolve(context):
    """ Add the initial board and discussions for each datacube
    """
    site = getSite()
    cat = getToolByName(context, 'portal_catalog')
    wf = getToolByName(context, 'portal_workflow')
    count = 0

    board = site.get('board')

    if not board:
        site.invokeFactory('Ploneboard', 'board')
        board = site.get('board')
        logger.info('Created discussion board: %s', board.absolute_url())

    brains = cat.searchResults(portal_type="DataCube", Language="all")

    for brain in brains:
        obj = brain.getObject()
        board.invokeFactory('PloneboardForum', obj.id)

        forum = board[obj.id]
        forum.setTitle(obj.Title())

        wf.doActionFor(forum, 'make_moderated')

        forum.reindexObject()

        logger.info('Created forum: %s', forum.title)

        count += 1
        total = len(brains)

        if count % 100 == 0:
            logger.info('INFO: Subtransaction committed to zodb (%s/%s)',
                        count, total)
            transaction.commit()

    logger.info('Done creating forums')
