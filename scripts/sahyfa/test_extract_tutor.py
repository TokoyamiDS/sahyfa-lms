import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("extract_tutor.py")
SPEC = importlib.util.spec_from_file_location("extract_tutor", MODULE_PATH)
extract_tutor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(extract_tutor)


def test_external_video_is_classified_as_external_video():
    post = {"post_type": "lesson"}
    meta = {"_video": 'a:1:{s:6:"source";s:12:"external_url";}'}

    assert extract_tutor.infer_activity(post, meta) == "external_video"


def test_shortcode_video_is_classified_as_embed():
    post = {"post_type": "lesson"}
    meta = {"_video": 'a:1:{s:6:"source";s:9:"shortcode";}'}

    assert extract_tutor.infer_activity(post, meta) == "embed"


def test_bundle_lesson_is_preserved_when_it_has_no_video_metadata():
    post = {"post_type": "cb-lesson"}

    assert extract_tutor.infer_activity(post, {}) == "bundle_lesson"


def test_regular_lesson_defaults_to_dynamic_page():
    post = {"post_type": "lesson"}

    assert extract_tutor.infer_activity(post, {}) == "dynamic_page"
