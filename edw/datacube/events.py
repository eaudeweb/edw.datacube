""" Event handlers
"""
from zope.component.hooks import getSite
from Products.CMFCore.utils import getToolByName

# WIP clone the charts from the cloneFrom DataSet to the newly created DataSet
def handle_dataset_added(obj, event):
    """Clone charts for the new dataset
    """
    site = getSite()
    cat = getToolByName(site, 'portal_catalog')
    cloneFrom_id = obj.getField('cloneFrom').getAccessor(obj)()
    cloneFrom = site.reference_catalog.lookupObject(cloneFrom_id)
    charts = cloneFrom.getBRefs()
