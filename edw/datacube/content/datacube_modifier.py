from zope.component import adapts
from zope.component import queryUtility
from zope.interface import implements
from archetypes.schemaextender.interfaces import ISchemaModifier
from plone.registry.interfaces import IRegistry
from edw.datacube.interfaces import IDataCube
from edw.datacube.interfaces import IDataCubeSettings
from edw.datacube.interfaces import defaults


class DataCubeModifier(object):
    adapts(IDataCube)
    implements(ISchemaModifier)

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        cubeSettings = queryUtility(
                IRegistry).forInterface(IDataCubeSettings, False)
        endpoint = getattr(cubeSettings, "default_sparql_endpoint",
                defaults.DEFAULT_SPARQL_ENDPOINT)
        schema["endpoint"].default = endpoint
