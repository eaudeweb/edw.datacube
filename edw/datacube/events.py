""" Event handlers
"""
from edw.datacube.utils import clone
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFCore.utils import getToolByName
from zope.component.hooks import getSite
import zope.event

def handle_dataset_added(obj, event):
    """Clone charts from the cloneFrom dataset to the new dataset
    """
    site = getSite()
    cloneFrom_id = obj.getField('cloneFrom').getAccessor(obj)()
    cloneFrom = site.reference_catalog.lookupObject(cloneFrom_id)

    if cloneFrom:
        charts = cloneFrom.getBRefs()
        for chart in charts:
            clone(chart, obj)

def handle_content_state_changed(obj, event):
    """Add forum for published DataCube objects
    Make moderated forum when DataCube is published, otherwise private
    """
    _marker = object()
    site = getSite()
    wf = getToolByName(site, 'portal_workflow')
    board = site.get('board')

    def do_wf(obj, wf_state):
        wf.doActionFor(obj, wf_state)
        forum.reindexObject()

    if board:
        wflow = event.workflow.getInfoFor(obj, 'review_state', _marker)
        if wflow == 'published':
            forum = board.get(obj.id)
            if not forum:
                board.invokeFactory('PloneboardForum', id=obj.id,
                                    title=obj.Title())
                forum = board.get(obj.id)
                zope.event.notify(ObjectInitializedEvent(forum))
            if wf.getInfoFor(forum, 'review_state') != 'moderated':
                do_wf(forum, 'make_moderated')
        else:
            forum = board.get(obj.id)
            if forum:
                if wf.getInfoFor(forum, 'review_state') != 'private':
                    do_wf(forum, 'make_private')
