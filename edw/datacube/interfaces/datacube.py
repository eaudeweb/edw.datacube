""" Interfaces
"""
from zope.interface import Interface
from zope import schema
from zope.i18nmessageid import MessageFactory
_ = MessageFactory("edw")

import defaults


class IDataCube(Interface):
    """Description of the Example Type"""

    # -*- schema definition goes here -*-



class IDataCubeSettings(Interface):
    """ Settings for datacube
    """
    datacube_thumbnail = schema.TextLine(
            title=_(u"DataCube thumbnail"),
            description=_(u"Default picture URL when no thumbnail is available"),
            required=True,
            default=defaults.DATACUBE_THUMBNAIL
    )

    visualization_thumbnail = schema.TextLine(
            title=_(u"Visualization thumbnail"),
            description=_(u"Default picture URL when no thumbnail is available"),
            required=True,
            default=defaults.VISUALIZATION_THUMBNAIL
    )

    default_sparql_endpoint = schema.TextLine(
            title=_(u"DEFAULT_SPARQL_ENDPOINT"),
            description=_(u"Default SPARQL Endpoint for datacubes"),
            required=True,
            default=defaults.DEFAULT_SPARQL_ENDPOINT
    )

    default_user_sparql_endpoint = schema.TextLine(
            title=_(u"DEFAULT_USER_SPARQL_ENDPOINT"),
            description=_(u"Default SPARQL Endpoint for indicators"),
            required=True,
            default=defaults.DEFAULT_USER_SPARQL_ENDPOINT
    )

    default_cr_url = schema.TextLine(
            title=_(u"DEFAULT_CR_URL"),
            description=_(u"Default Content Registry URL"),
            required=True,
            default=defaults.DEFAULT_CR_URL
    )

    find_countries_query = schema.Text(
            title=_(u"Find countries url query"),
            description=_(u"URL query used for the indicators Find countries url."),
            required=True,
            default=defaults.FIND_COUNTRIES_QUERY,
    )

    find_breakdowns_query = schema.Text(
            title=_(u"Find breakdowns url query"),
            description=_(u"URL query used for the indicators Find breakdowns url."),
            required=True,
            default=defaults.FIND_BREAKDOWNS_QUERY,
    )

