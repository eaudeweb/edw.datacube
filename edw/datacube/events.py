""" Event handlers
"""
from edw.datacube.utils import clone
from Products.CMFCore.utils import getToolByName
from zope.component.hooks import getSite

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
    """
    _marker = object()
    if event.workflow.getInfoFor(obj, 'review_state', _marker) == 'published':
        site = getSite()
        wf = getToolByName(site, 'portal_workflow')

        board = site.get('board')
        if board:
            board.invokeFactory('PloneboardForum', id=obj.id, title=obj.Title())
            forum = board.get(obj.id)
            wf.doActionFor(forum, 'make_moderated')
            forum.reindexObject()
