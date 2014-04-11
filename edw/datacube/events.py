""" Event handlers
"""
from zope.component.hooks import getSite
from edw.datacube.utils import clone


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
