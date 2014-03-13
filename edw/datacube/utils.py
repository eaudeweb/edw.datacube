from Acquisition import aq_base
from DateTime import DateTime
from Persistence import PersistentMapping
from Products.CMFPlone import utils

hasNewDiscussion = True
try:
    from plone.app.discussion.interfaces import IConversation
except ImportError:
    hasNewDiscussion = False


def clone(obj, new_dataset, reindex=True):
    """Create a new version of an object

    This is done by copy&pasting the object, then assigning, as
    versionId, the one from the original object.

    Additionally, we rename the object using a number based scheme and
    then clean it up to avoid various problems.
    """

    obj_id = obj.getId()
    parent = utils.parent(obj)

    # Create copy of the object
    clipb = parent.manage_copyObjects(ids=[obj_id])
    res = parent.manage_pasteObjects(clipb)

    new_id = res[0]['new_id']

    new_chart = getattr(parent, new_id)

    # Set effective date today
    new_chart.setCreationDate(DateTime())
    new_chart.setEffectiveDate(None)

    # Remove comments
    if hasNewDiscussion:
        conversation = IConversation(new_chart)
        while conversation.keys():
            conversation.__delitem__(conversation.keys()[0])
    else:
        if hasattr(aq_base(new_chart), 'talkback'):
            tb = new_chart.talkback
            if tb is not None:
                for obj in tb.objectValues():
                    obj.__of__(tb).unindexObject()
                tb._container = PersistentMapping()

    # Set new related DataSet
    new_chart.setRelatedItems([new_dataset])

    if reindex:
        new_chart.reindexObject()

    return new_chart
