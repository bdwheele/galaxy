import pytest

from galaxy.config import BaseAppConfiguration
from galaxy.config.schema import AppSchema


MOCK_DEPRECATED_DIRS = {
    'my_config_dir': 'old-config',
    'my_data_dir': 'old-database',
}

# Mock properties loaded from schema (all options represent paths)
MOCK_SCHEMA = {
    'my_config_dir': {
        'type': 'str',
        'default': 'my-config',
    },
    'my_data_dir': {
        'type': 'str',
        'default': 'my-data',
    },
    'path1': {
        'type': 'str',
        'default': 'my-config-files',
        'path_resolves_to': 'my_config_dir',
    },
    'path2': {
        'type': 'str',
        'default': 'my-data-files',
        'path_resolves_to': 'my_data_dir',
    },
    'path3': {
        'type': 'str',
        'default': 'my-other-files',
    }
}


def get_schema(app_mapping):
    return {'mapping': {'_': {'mapping': app_mapping}}}


@pytest.fixture
def mock_init(monkeypatch):
    monkeypatch.setattr(BaseAppConfiguration, '_load_schema', lambda a: AppSchema(None, '_'))
    monkeypatch.setattr(AppSchema, '_read_schema', lambda a, b: get_schema(MOCK_SCHEMA))
    monkeypatch.setattr(BaseAppConfiguration, 'deprecated_dirs', MOCK_DEPRECATED_DIRS)


def test_mock_schema_is_loaded(mock_init):
    # Check that mock is loaded as expected
    config = BaseAppConfiguration()
    assert len(config._raw_config) == 5
    assert config._raw_config['my_config_dir'] == 'my-config'
    assert config._raw_config['my_data_dir'] == 'my-data'
    assert config._raw_config['path1'] == 'my-config-files'
    assert config._raw_config['path2'] == 'my-data-files'
    assert config._raw_config['path3'] == 'my-other-files'


def test_no_kwargs(mock_init):
    # Expected: use default from schema, then resolve
    config = BaseAppConfiguration()
    assert config.path1 == 'my-config/my-config-files'  # resolved
    assert config.path2 == 'my-data/my-data-files'  # resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_relative_path(mock_init):
    # Expected: use value from kwargs, then resolve
    new_path1 = 'foo1/bar'
    new_path2 = 'foo2/bar'
    config = BaseAppConfiguration(path1=new_path1, path2=new_path2)

    assert config.path1 == 'my-config/' + new_path1  # resolved
    assert config.path2 == 'my-data/' + new_path2  # resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_ablsolute_path(mock_init):
    # Expected: use value from kwargs, do NOT resolve
    new_path1 = '/foo1/bar'
    new_path2 = '/foo2/bar'
    config = BaseAppConfiguration(path1=new_path1, path2=new_path2)

    assert config.path1 == new_path1  # NOT resolved
    assert config.path2 == new_path2  # NOT resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_relative_path_old_prefix(mock_init):
    # Expect: use value from kwargs, strip old prefix, then resolve
    new_path1 = 'old-config/foo1/bar'
    new_path2 = 'old-database/foo2/bar'
    config = BaseAppConfiguration(path1=new_path1, path2=new_path2)

    assert config.path1 == 'my-config/foo1/bar'  # stripped of old prefix, resolved
    assert config.path2 == 'my-data/foo2/bar'  # stripped of old prefix, resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_relative_path_old_prefix_for_other_option(mock_init):
    # Expect: use value from kwargs, do NOT strip old prefix, then resolve
    # Reason: deprecated dirs are option-specific: we don't want to strip 'old-config'
    # (deprecated for the config_dir option) if it's used for another option
    new_path1 = 'old-database/foo1/bar'
    new_path2 = 'old-config/foo2/bar'
    config = BaseAppConfiguration(path1=new_path1, path2=new_path2)

    assert config.path1 == 'my-config/' + new_path1  # resolved
    assert config.path2 == 'my-data/' + new_path2  # resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_relative_path_old_prefix_empty_after_strip(mock_init):
    # Expect: use value from kwargs, strip old prefix, then resolve
    new_path1 = 'old-config'
    config = BaseAppConfiguration(path1=new_path1)

    assert config.path1 == 'my-config/'  # stripped of old prefix, then resolved
    assert config.path2 == 'my-data/my-data-files'  # stripped of old prefix, then resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_set_to_null(mock_init):
    # Expected: allow overriding with null, then resolve
    # This is not a common scenario, but it does happen: one example is
    # `job_config` set to `None` when testing
    config = BaseAppConfiguration(path1=None)

    assert config.path1 == 'my-config'  # resolved
    assert config.path2 == 'my-data/my-data-files'  # resolved
    assert config.path3 == 'my-other-files'  # no change


def test_add_sample_file(mock_init, monkeypatch):
    # Expected: sample file appended to list of defaults, then selected
    # - resolved w.r.t sample-dir (_in_sample_dir mocked)
    # - has ".sample" suffix
    monkeypatch.setattr(BaseAppConfiguration, 'add_sample_file_to_defaults', {'path1'})
    monkeypatch.setattr(BaseAppConfiguration, '_in_sample_dir', lambda a, path: '/sample-dir/%s' % path)
    config = BaseAppConfiguration()

    assert config._raw_config['path1'] == 'my-config-files'
    assert config.path1 == '/sample-dir/my-config-files.sample'


def test_select_one_path_from_list(mock_init, monkeypatch):
    # Expected: files do not exist, so use last file in list (would be sample file); value is not a list
    monkeypatch.setattr(BaseAppConfiguration, 'add_sample_file_to_defaults', {'path1'})
    monkeypatch.setattr(BaseAppConfiguration, '_in_sample_dir', lambda a, path: '/sample-dir/%s' % path)
    config = BaseAppConfiguration()

    assert config._raw_config['path1'] == 'my-config-files'
    assert config.path1 == '/sample-dir/my-config-files.sample'


def test_select_one_path_from_list_all_files_exist(mock_init, monkeypatch):
    # Expected: all files exist, so use first file in list; value is not a list
    monkeypatch.setattr(BaseAppConfiguration, 'add_sample_file_to_defaults', {'path1'})
    monkeypatch.setattr(BaseAppConfiguration, '_path_exists', lambda a, b: True)
    config = BaseAppConfiguration()

    assert config._raw_config['path1'] == 'my-config-files'
    assert config.path1 == 'my-config/my-config-files'
