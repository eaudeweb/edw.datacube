import time
import urllib
import urllib2
import os
import logging
from collections import defaultdict
import threading
import jinja2
import sparql

from decimal import Decimal

SPARQL_DEBUG = bool(os.environ.get('SPARQL_DEBUG') == 'on')

logger = logging.getLogger(__name__)

sparql_env = jinja2.Environment(loader=jinja2.PackageLoader(__name__))
sparql_env.filters.update({
    'literal_n3': lambda value: sparql.Literal(value).n3(),
    'uri_n3': lambda value: sparql.IRI(value).n3(),
})


class QueryError(Exception):
    pass


class DataCache(object):

    def __init__(self):
        self.data = {}
        self.timestamp = None
        self.lock = threading.Lock()

    def ping(self, timestamp):
        with self.lock:
            if timestamp != self.timestamp:
                self.data.clear()
                self.timestamp = timestamp

    def get(self, key, update):
        with self.lock:
            if key not in self.data:
                self.data[key] = update()
            return self.data[key]


data_cache = DataCache()


class NotationMap(object):

    NAMESPACES = [
        ('breakdown', 'http://semantic.digital-agenda-data.eu/'
                      'codelist/breakdown/'),
        ('indicator', 'http://semantic.digital-agenda-data.eu/'
                      'codelist/indicator/'),
        ('breakdown-group', 'http://semantic.digital-agenda-data.eu/'
                            'codelist/breakdown-group/'),
        ('time-period', 'http://reference.data.gov.uk/id/gregorian-year/'),
        ('flag', 'http://eurostat.linked-statistics.org/dic/flags#'),
        ('indicator-group', 'http://semantic.digital-agenda-data.eu/'
                            'codelist/indicator-group/'),
        ('unit-measure', 'http://semantic.digital-agenda-data.eu/'
                         'codelist/unit-measure/'),
        ('ref-area', 'http://eurostat.linked-statistics.org/dic/geo#'),
    ]

    def __init__(self, cube):
        self.cube = cube

        self.NS_DIMENSIONS = {}
        for item in self.cube.get_dimensions(flat=True):
            code = item['notation']
            uri = item['dimension']
            if code is None:
                code = uri.split('/')[-1]
            self.NS_DIMENSIONS.update({code: uri})

    def update(self):
        t0 = time.time()
        logger.info('loading notation cache')
        query = sparql_env.get_template('notations.sparql').render(**{
            'dataset': self.cube.dataset,
        })
        by_notation = defaultdict(dict)
        by_uri = {}
        for row in self.cube._execute(query):
            by_notation[row['namespace']][row['notation'].lower()] = row
            by_uri[row['uri']] = row
        logger.info('notation cache loaded, %.2f seconds', time.time() - t0)
        return {
            'by_notation': dict(by_notation),
            'by_uri': by_uri,
        }

    def get(self):
        cache_key = (self.cube.endpoint, self.cube.dataset)
        return data_cache.get(cache_key, self.update)

    def lookup_dimension_uri(self, dimension_code):
        return {
            'uri': dict(self.NS_DIMENSIONS).get(dimension_code),
            'namespace': dimension_code,
            'notation': None
        }

    def lookup_measure_uri(self):
        try:
            measure_key = [
                key for key in self.NS_DIMENSIONS.keys()
                if key.startswith('measure')
            ][0]
            return {
                'uri': self.NS_DIMENSIONS[measure_key],
                'namespace': measure_key.replace('measure#', ''),
                'notation': None
            }
        except IndexError:
            return None

    def lookup_notation(self, namespace, notation):
        data = self.get()
        by_notation = data['by_notation']
        notation = notation.lower()
        ns = by_notation.get(namespace)
        if ns is None:
            raise RuntimeError("Unknown namespace %r", namespace)
        rv = ns.get(notation)
        if rv is None:
            if namespace in ['unit-measure', 'breakdown', 'indicator']:
                uri = dict(self.NAMESPACES)[namespace] + notation,
                rv = self._add_item(data, uri, namespace, notation)
            else:
                logger.warn('lookup failure %r', (namespace, notation))
        return rv

    def lookup_uri(self, uri):
        by_uri = self.get()['by_uri']
        return by_uri.get(uri)

    @staticmethod
    def _add_item(data, uri, namespace, notation):
        logger.warn('patching missing notation %r', (namespace, notation))
        row = {'uri': uri,
               'namespace': namespace,
               'notation': notation}
        data['by_uri'][uri] = row
        data['by_notation'][namespace][notation] = row
        return row

    def touch_uri(self, uri):
        data = self.get()
        if uri not in data['by_uri']:
            for namespace, prefix in self.NAMESPACES:
                if uri.startswith(prefix):
                    notation = uri[len(prefix):]
                    self._add_item(data, uri, namespace, notation.lower())
                    break
            else:
                logger.warn('new unknown uri %r', uri)


class Cube(object):

    def __init__(self, endpoint, dataset):
        self.endpoint = endpoint
        self.dataset = dataset
        self.notations = NotationMap(self)

    def _execute(self, query, as_dict=True):
        t0 = time.time()
        if SPARQL_DEBUG:
            logger.info('Running query: \n%s', query)
        try:
            query_object = sparql.Service(self.endpoint).createQuery()
            query_object.method = 'POST'
            res = query_object.query(query)
        except urllib2.HTTPError, e:
            if SPARQL_DEBUG:
                logger.info('Query failed')
            if 400 <= e.code < 600:
                raise QueryError(e.fp.read())
            else:
                raise
        if SPARQL_DEBUG:
            logger.info('Query took %.2f seconds.', time.time() - t0)
        rv = (sparql.unpack_row(r) for r in res)
        if as_dict:
            return (dict(zip(res.variables, r)) for r in rv)
        else:
            return rv

    def get_datasets(self):
        query = sparql_env.get_template('datasets.sparql').render()
        return list(self._execute(query))

    def get_dataset_metadata(self, dataset):
        query = sparql_env.get_template('dataset_metadata.sparql').render(**{
            'dataset': dataset,
        })
        return list(self._execute(query))[0]

    def get_dataset_details(self):
        #sparql_template = 'dataset_details.sparql'
        sparql_template = 'indicator_time_coverage.sparql'
        query = sparql_env.get_template(sparql_template).render(**{
            'dataset': self.dataset,
        })

        # indicator, maxYear, minYear
        res = list(self._execute(query))
        res_by_uri = {row['indicator']: row for row in res}

        meta_list = self.get_dimension_option_metadata_list(
            'indicator', list(res_by_uri)
        )

        for meta in meta_list:
            uri = meta.pop('uri', None)
            #meta['altlabel'] = meta.pop('short_label', None)
            meta['sourcelabel'] = meta.pop('source_label', None)
            meta['sourcelink'] = meta.pop('source_url', None)
            meta['sourcenotes'] = meta.pop('source_notes', None)
            meta['notes'] = meta.pop('note', None)
            meta['longlabel'] = meta.pop('label', None)
            res_by_uri[uri].update(meta)


        def _sort_key(item):
            try:
                parent = int(item.get('parentOrder', None))
                inner = int(item.get('innerOrder', None))
            except (ValueError, TypeError):
                parent = None
                inner = None
            return (parent, inner,)

        return sorted(res, key=_sort_key)

    def get_dimension_labels(self, dimension, value):
        query = sparql_env.get_template('dimension_label.sparql').render(**{
            'dataset': self.dataset,
            'dimension': dimension,
            'value': value,
            'group_dimensions': self.get_group_dimensions(),
            'notations': self.notations,
        })
        rv = list(self._execute(query))
        if not rv:
            rv = [{'label': value, 'short_label': None}]
        return rv

    def get_dimensions(self, flat=False):
        query = sparql_env.get_template('dimensions.sparql').render(**{
            'dataset': self.dataset,
        })
        result = self._execute(query)
        if flat:
            return list(result)
        else:
            rv = defaultdict(list)
            for row in result:
                rv[row['type_label']].append({
                    'label': row['label'],
                    'notation': row['notation'],
                    'comment': row['comment'],
                })
            return dict(rv)

    def load_group_dimensions(self):
        query = sparql_env.get_template('group_dimensions.sparql').render(**{
            'dataset': self.dataset,
        })
        return sorted([r['group_notation'] for r in self._execute(query)])

    def get_group_dimensions(self):
        cache_key = (self.endpoint, self.dataset, 'get_group_dimensions')
        return data_cache.get(cache_key, self.load_group_dimensions)

    def get_dimension_options(self, dimension, filters=[]):
        # fake an n-dimensional query, with a single dimension, that has no
        # specific filters
        n_filters = [[]]
        return self.get_dimension_options_n(dimension, filters, n_filters)

    def get_dimension_options_xy(self, dimension,
                                 filters, x_filters, y_filters):
        n_filters = [x_filters, y_filters]
        return self.get_dimension_options_n(dimension, filters, n_filters)

    def get_other_labels(self, uri):
        if '#' in uri:
            uri_label = uri.split('#')[-1]
        else:
            uri_label = uri.split('/')[-1]
        return { "group_notation": None,
                 "label": uri_label,
                 "notation": uri_label,
                 "short_label": None,
                 "uri": uri,
                 "order": None }

    def get_dimension_options_xyz(self, dimension,
                                  filters, x_filters, y_filters, z_filters):
        n_filters = [x_filters, y_filters, z_filters]
        return self.get_dimension_options_n(dimension, filters, n_filters)

    def get_dimension_options_n(self, dimension, filters, n_filters):
        uris = None
        result_sets = []
        for extra_filters in n_filters:
            query = sparql_env.get_template('dimension_options.sparql').render(**{
                'dataset': self.dataset,
                'dimension_code': dimension,
                'filters': filters + extra_filters,
                'group_dimensions': self.get_group_dimensions(),
                'notations': self.notations,
            })
            result_sets.append(list(self._execute(query)))

        interval_types = set(item['interval_type']
                             for res in result_sets for item in res)

        if len(interval_types) > 1:
            # normalize to years
            def options(res):
                return set(item['parent_year'] or item['uri'] for item in res)

        else:
            def options(res):
                return set(item['uri'] for item in res)

        for res in result_sets:
            res = options(res)
            if uris is None:
                uris = res
            else:
                uris = uris & res

        labels = self.get_labels(uris)
        rv = [labels.get(uri, self.get_other_labels(uri)) for uri in uris]
        rv.sort(key=lambda item: int(item.pop('order') or '0'))
        return rv

    def get_labels(self, uri_list):
        if len(uri_list) < 1:
            return {}
        tmpl = sparql_env.get_template('labels.sparql')
        for uri in uri_list:
            self.notations.touch_uri(uri)
        query = tmpl.render(**{
            'uri_list': uri_list,
        })
        return {row['uri']: row for row in self._execute(query)}

    def get_dimension_option_metadata_list(self, dimension, uri_list):
        tmpl = sparql_env.get_template('dimension_option_metadata.sparql')
        query = tmpl.render(**{
            'dataset': self.dataset,
            'uri_list': uri_list,
            'dimension': dimension
        })
        res = list(self._execute(query))
        return [{k: row[k] for k in row if row[k] is not None} for row in res]

    def get_dimension_option_metadata(self, dimension, option):
        uri = self.notations.lookup_notation(dimension, option)['uri']
        res = self.get_dimension_option_metadata_list(dimension, [uri])
        if res:
            return res[0]
        else:
            return {}

    def get_columns(self):
        columns_map = {}
        for item in self.get_dimensions(flat=True):
            if item['type_label'] in ['measure', 'dimension group']:
                continue
            name = item['notation']
            if name not in columns_map:
                columns_map[name] = {
                    "uri": item['dimension'],
                    "optional": True,
                    "notation": item['notation'],
                    "name": name,
                }
            if item['type_label'] != 'attribute':
                columns_map[name]['optional'] = False
        return columns_map.values()

    def get_observations(self, filters):
        columns = self.get_columns()
        query = sparql_env.get_template('data_and_attributes.sparql').render(**{
            'dataset': self.dataset,
            'columns': columns,
            'filters': filters,
            'group_dimensions': self.get_group_dimensions(),
            'notations': self.notations,
        })
        result = list(self._execute(query, as_dict=False))
        def reducer(memo, item):
            def uri_filter(uri):
                if uri:
                    return True if uri.startswith('http://') else False
            return memo.union(set(filter(uri_filter, item[:-1])))
        uris = reduce(reducer, result, set())
        column_names = [item['notation'] for item in columns] + ['value']
        return self._format_observations_result(result, column_names, uris)

    def _format_observations_result(self, result, columns, uris):
        labels = self.get_labels(uris)

        for row in result:
            result_row = []
            value = row.pop(-1)
            for item in row:
                if item not in uris:
                    result_row.append(item)
                else:
                    notation = labels.get(item, {}).get('notation', None)
                    label = labels.get(item, {}).get('label', None)
                    if notation is None:
                        notation = self.get_other_labels(item).get('notation', None)
                        label = self.get_other_labels(item).get('label', None)
                    result_row.append(
                        {'notation': notation,
                         'inner_order': labels.get(item, {}).get('inner_order', None),
                         'label': label,
                         'short-label': labels.get(item, {}).get('short_label', None)}
                    )
            if type(value) == type(Decimal()):
                value = float(value)
            result_row.append(value)
            yield dict(zip(columns, result_row))

    def get_observations_cp(self, filters, whitelist_items):
        columns = self.get_columns()

        indicator_group = dict(filters)['indicator-group']
        whitelist = []
        for item in whitelist_items:
            mapped_item = {}
            if item['indicator-group'].lower() == indicator_group.lower():
                for n, col in enumerate(columns, 1):
                    name = col['notation']
                    if name in ['indicator', 'breakdown', 'unit-measure']:
                        mapped_item[n] = self.notations.lookup_notation(
                                            name, item[name])['uri']
                whitelist.append(mapped_item)
        if not whitelist:
            return []
        query = sparql_env.get_template('data_and_attributes_cp.sparql').render(**{
            'dataset': self.dataset,
            'columns': columns,
            'filters': filters,
            'group_dimensions': self.get_group_dimensions(),
            'notations': self.notations,
            'whitelist': whitelist,
        })
        result = list(self._execute(query, as_dict=False))
        def reducer(memo, item):
            def uri_filter(uri):
                if uri:
                    return True if uri.startswith('http://') else False
            return memo.union(set(filter(uri_filter, item[:-1])))
        uris = reduce(reducer, result, set())
        column_names = [item['notation'] for item in columns] + ['value']
        return self._format_observations_result(result, column_names, uris)

    def get_data_xy(self, join_by, filters, x_filters, y_filters):
        n_filters = [x_filters, y_filters]
        return self.get_data_n(join_by, filters, n_filters)

    def get_data_xyz(self, join_by, filters, x_filters, y_filters,
                     z_filters):
        n_filters = [x_filters, y_filters, z_filters]
        return self.get_data_n(join_by, filters, n_filters)

    def get_data_n(self, join_by, filters, n_filters):
        # GET COLUMNS AND COLUMNS NAMES
        columns = self.get_columns()
        columns_names = [item['notation'] for item in columns] + ['value']

        # GET DATA AND ATTRIBUTES
        raw_data = []
        idx = 0
        for extra_filters in n_filters:
            query = sparql_env.get_template('data_and_attributes.sparql').render(**{
                'dataset': self.dataset,
                'columns': columns,
                'filters': filters + list(extra_filters),
                'group_dimensions': self.get_group_dimensions(),
                'notations': self.notations,
            })
            container = {}
            data = self._execute(query, as_dict=False)
            dict_data = []
            for item in data:
                if type(item[-1]) == type(Decimal()):
                    item[-1] = float(item[-1])
                dict_data.append(
                        dict(zip(columns_names, item)))

            # only keep the entry with largest time_period value
            time_periods = {}
            for row in dict_data:
                join_vaule = row[join_by]
                time_periods[join_vaule] = max([time_periods.get(join_vaule),
                                                row['time-period']])
            dict_data = [row for row in dict_data
                         if time_periods[row[join_by]] == row['time-period']]
            raw_data.append(dict_data)

        # JOIN DATA
        def find_common(memo, item):
            join_set = [it[join_by] for it in item]
            temp_common = set(memo).intersection(set(join_set))
            return temp_common
        common = reduce(find_common, raw_data, [it[join_by] for it in raw_data[0]])

        # EXTRACT UNIQUE URIS FROM DATA
        by_category = defaultdict(list)
        uri_set = set()
        for obs_set in raw_data:
            for obs in obs_set:
                if obs[join_by] in common:
                    by_category[obs[join_by]].append(obs)
                    for key, value in obs.items():
                        if isinstance(value, basestring) and value.startswith('http://'):
                            uri_set.add(value)

        # GET LABELS FOR URIS
        labels = self.get_labels(uri_set)

        filtered_data = []
        # EXTRACT COMMON ROWS
        dimensions = ['x', 'y', 'z']
        single_keys = [f[0] for f in filters] + [join_by]
        for obs_list in by_category.values():
            idx = 0
            out = defaultdict(dict)
            for obs in obs_list:
                for key in columns_names:
                    if key not in single_keys:
                        out[key][dimensions[idx]] = obs[key]
                    else:
                        out[key] = obs[key]
                for k, v in out.items():
                    if k not in single_keys:
                        uri_labels = labels.get(v[dimensions[idx]], v[dimensions[idx]])
                        if uri_labels:
                            out[k][dimensions[idx]] = uri_labels
                    else:
                        uri_labels = labels.get(v, None)
                        if uri_labels:
                            out[k] = uri_labels
                idx+=1
            filtered_data.append(out)
        return filtered_data


    def get_revision(self):
        query = sparql_env.get_template('last_modified.sparql').render()
        timestamp = unicode(next(self._execute(query))['modified'])
        data_cache.ping(timestamp)
        return timestamp

    def dump(self, data_format=''):
        query = sparql_env.get_template('dump.sparql').render(**{
            'dataset': self.dataset,
            'notations': self.notations
        })
        if data_format:
            params = urllib.urlencode({
                'query': query,
                'format': data_format,
            })
            result = urllib2.urlopen(self.endpoint, data=params)
            return result.read()
        return self._execute(query)
