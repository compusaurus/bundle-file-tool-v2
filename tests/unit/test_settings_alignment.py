"""Settings must reach the consuming renderer, not merely pass schema validation."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from core import splash
from core.config_setup import validate_document
from core.service import BundleToolService
from core.user_state import UserStateStore
from web.adapter import WebAdapter

ROOT = Path(__file__).resolve().parents[2]


def splash_profile(monkeypatch, tmp_path):
    profile = splash.read_splash_profile()
    profile['media']['media_sources'] = [str(splash.SPLASH_ASSET_ROOT / 'videos'), str(splash.SPLASH_ASSET_ROOT)]
    path = tmp_path / 'profile.json'
    path.write_text(json.dumps(profile), encoding='utf-8')
    monkeypatch.setattr(splash, 'SPLASH_PROFILE_TEMPLATE', path)
    return profile, path


def test_square_presentation_is_shared_by_native_and_web():
    profile = splash.read_splash_profile()
    assert profile['geometry']['shape'] == 'rect'
    assert splash.web_splash_settings()['shape'] == 'rect'
    assert profile['geometry']['rounded_corners']['radius_px'] == 0


def test_native_enablement_stops_before_runtime_probe(monkeypatch, tmp_path):
    profile, path = splash_profile(monkeypatch, tmp_path)
    profile['interfaces']['native']['enabled'] = False
    path.write_text(json.dumps(profile), encoding='utf-8')
    monkeypatch.setattr(splash, '_runtime_available', lambda: pytest.fail('disabled splash probed runtime'))
    assert splash.run_startup_splash(environment={}).status == 'disabled'
    assert splash.web_splash_settings()['enabled'] == 'true'


def test_web_profile_honors_disabled_flag_and_media_geometry(monkeypatch, tmp_path):
    profile, path = splash_profile(monkeypatch, tmp_path)
    profile['interfaces']['web']['enabled'] = False
    profile['geometry'].update(shape='oval', scale_percent=32, is_native=True)
    profile['media']['video']['temporal'].update(start_pos_ms=1250, end_pos_ms=6500)
    profile['media']['video']['loop_behavior'] = 'freeze'
    profile['runtime_behavior']['close_on_click'] = False
    path.write_text(json.dumps(profile), encoding='utf-8')
    settings = splash.web_splash_settings()
    assert settings['enabled'] == 'false'
    assert settings['shape'] == 'oval' and settings['scale-percent'] == 32
    assert 'is-native' not in settings  # Native means OS window frame, not media dimensions.
    assert settings['start-pos-ms'] == 1250 and settings['end-pos-ms'] == 6500
    assert settings['loop-behavior'] == 'freeze' and settings['close-on-click'] == 'false'


def test_selected_image_and_custom_log_location_are_resolved(monkeypatch, tmp_path):
    profile, path = splash_profile(monkeypatch, tmp_path)
    profile['media']['media_type'] = 'image'
    profile['media']['image']['static_duration_ms'] = 3200
    profile['logging']['log_file'] = 'custom/splash.log'
    path.write_text(json.dumps(profile), encoding='utf-8')
    monkeypatch.setattr(splash, 'startup_log_directory', lambda: tmp_path / 'logs')
    assert splash.splash_media_path() == splash.SPLASH_ASSET_ROOT / 'bft-icon.png'
    assert splash.web_splash_settings()['static-duration-ms'] == 3200
    materialized = json.loads(splash._runtime_profile(tmp_path / 'runtime.json').read_text())
    assert materialized['logging']['log_file'] == str(tmp_path / 'logs/custom/splash.log')


def test_invalid_splash_profile_is_nonfatal(monkeypatch, tmp_path):
    profile, path = splash_profile(monkeypatch, tmp_path)
    profile.pop('geometry')
    path.write_text(json.dumps(profile), encoding='utf-8')
    monkeypatch.setattr(splash, '_runtime_available', lambda: True)
    assert splash.run_startup_splash(environment={}, runner=lambda *a, **kw: pytest.fail('bad profile ran')).status == 'failed'
    assert splash.web_splash_settings()['enabled'] == 'false'


def test_progress_profile_reaches_both_renderers(monkeypatch, tmp_path):
    from ui import progress_profile, tk_progress
    from cli_progress import PyThermXReporter, build_reporter
    profile = json.loads(progress_profile.PROFILE_PATH.read_text())
    profile['tkinter'].update(width=480, show_elapsed=False, show_rate=False)
    profile['terminal'].update(width=33, show_rate=False)
    profile['advanced'].update(pump_interval_ms=50, drain_budget=200, queue_capacity=4000)
    path = tmp_path / 'progress.json'
    path.write_text(json.dumps(profile), encoding='utf-8')
    monkeypatch.setattr(progress_profile, 'PROFILE_PATH', path)
    style = tk_progress.default_style()
    assert style.width == 480 and not style.show_elapsed and not style.show_rate
    assert (style.pump_interval_ms, style.drain_budget, style.queue_capacity) == (50, 200, 4000)
    cli = PyThermXReporter()
    assert cli._style.width == 33 and not cli._style.show_rate
    profile['enabled'] = False
    path.write_text(json.dumps(profile), encoding='utf-8')
    assert build_reporter('bar') is None
    assert tk_progress.run_with_progress(None, 'disabled', lambda **kwargs: kwargs) == {'progress':None, 'cancel':None}


def test_web_defaults_follow_governed_settings_and_remembered_source(tmp_path):
    settings = {
        'global_settings.input_dir':'/chosen/input', 'global_settings.output_dir':'/chosen/output',
        'app_defaults.default_mode':'unbundle', 'app_defaults.overwrite_policy':'skip',
        'app_defaults.add_headers':False, 'app_defaults.dry_run_default':True,
    }
    service = BundleToolService(config=SimpleNamespace(get=lambda key, default=None: settings.get(key, default)))
    state = UserStateStore(str(tmp_path / 'state.json'))
    adapter = WebAdapter(service, state=state)
    try:
        defaults = adapter.bootstrap()['defaults']
        assert defaults['source_path'] == '/chosen/input'
        assert defaults['extract_output_dir'] == '/chosen/output'
        assert defaults['default_mode'] == 'unbundle' and defaults['overwrite_policy'] == 'skip'
        assert not defaults['add_headers'] and defaults['dry_run']
        state.set('last_source_dir', '/remembered/source')
        assert adapter.bootstrap()['defaults']['source_path'] == '/remembered/source'
    finally:
        adapter.close()


def test_inactive_settings_cannot_be_changed_and_jsonl_is_not_offered():
    baseline = json.loads((ROOT / 'bundle_config.json').read_text())
    candidate = copy.deepcopy(baseline)
    candidate['app_defaults']['eol'] = 'CRLF'
    assert any(issue.rule_id == 'bft.read_only' for issue in validate_document(candidate, baseline))
    candidate = copy.deepcopy(baseline)
    candidate['app_defaults']['bundle_profile'] = 'jsonl'
    assert any(issue.severity == 'ERROR' for issue in validate_document(candidate, baseline))


def test_configured_log_folder_matches_viewer_root(monkeypatch, tmp_path):
    from core.config import ConfigManager
    from core.logging import configured_log_directory
    monkeypatch.setattr(ConfigManager, 'get', lambda self, key, default=None: 'operation-logs')
    monkeypatch.setattr(ConfigManager, 'governed_config_path', classmethod(lambda cls: tmp_path / 'bundle_config.json'))
    assert configured_log_directory() == str(tmp_path / 'operation-logs')
