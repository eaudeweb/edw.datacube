"""Add ploneboard and necessary discussions
"""
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFCore.utils import getToolByName
from zope.component.hooks import getSite
import logging
import transaction
import zope.event
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
        zope.event.notify(ObjectInitializedEvent(board))
        logger.info('Created discussion board: %s', board.absolute_url())

    brains = cat.searchResults(portal_type="DataCube", Language="all")

    for brain in brains:
        obj = brain.getObject()

        if wf.getInfoFor(obj, 'review_state') == 'published':
            board.invokeFactory('PloneboardForum', id=obj.id, title=obj.Title())

            forum = board[obj.id]
            zope.event.notify(ObjectInitializedEvent(forum))
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
