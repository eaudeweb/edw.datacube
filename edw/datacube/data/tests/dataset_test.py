from mock import ANY
from .base import sparql_test, create_cube


@sparql_test
def test_all_datasets_query_returns_the_dataset():
    cube = create_cube()
    res = cube.get_datasets()
    dataset = {
        'uri': ('http://semantic.digital-agenda-data.eu/'
                'dataset/digital-agenda-scoreboard-key-indicators'),
        'title': 'Digital Agenda Scoreboard Dataset',
    }
    assert dataset in res


@sparql_test
def test_dataset_metadata():
    cube = create_cube()
    res = cube.get_dataset_metadata(cube.dataset)
    assert res['title'] == "Digital Agenda Scoreboard Dataset"
    #assert "You can also browse the data" in res['description']
    #assert res['license'].startswith('http://')

@sparql_test
def test_dataset_dimensions_metadata():
    cube = create_cube()
    res = cube.get_dimensions()
    assert {'notation': 'ref-area',
            'label': "Country",
            'comment': ANY} in res['dimension']
    notations = lambda type_label: [d['notation'] for d in res[type_label]]
    assert sorted(res) == ['attribute', 'dimension',
                           'dimension group', 'measure']
    assert notations('dimension') == ['indicator', 'breakdown', 'unit-measure',
                                      'ref-area', 'time-period']
    assert sorted(notations('dimension group')) == ['breakdown-group',
                                            'indicator-group']
    assert sorted(notations('attribute')) == ['flag', 'note', 'unit-measure']
    assert [d['label'] for d in res['measure']] == ['Observation']

@sparql_test
def test_dataset_dimensions_flat_list():
    cube = create_cube()
    res = cube.get_dimensions(flat=True)
    assert sorted([d['notation'] for d in res]) == [
        'breakdown',
        'breakdown-group',
        'flag',
        'indicator',
        'indicator-group',
        'note',
        'obsValue',
        'ref-area',
        'time-period',
        'unit-measure',
        'unit-measure',
    ]

@sparql_test
def test_get_dataset_details():
    cube = create_cube()
    res = cube.get_dataset_details()
    by_notation = {r['notation']: r for r in res}
    i_iusell = by_notation['i_iusell']
    assert "selling online" in i_iusell.get('short_label', '').lower()
    assert "in the last 3 months" in i_iusell['definition']
    assert i_iusell['groupName'] == "eCommerce"
    assert i_iusell['sourcelabel'] == "Eurostat - ICT Households survey"
    assert "Extraction from HH/Indiv" in i_iusell['sourcenotes']
    assert i_iusell['sourcelink'] == (
            'http://ec.europa.eu/eurostat'
            '/web/information-society/data/comprehensive-database')
