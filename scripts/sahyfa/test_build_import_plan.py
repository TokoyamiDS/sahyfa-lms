import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("build_import_plan.py")
SPEC = importlib.util.spec_from_file_location("build_import_plan", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_plan_preserves_course_chapter_activity_relationships():
    document = {
        "schema_version": 1,
        "courses": [{"id": "10", "title": "Course", "content": "Intro"}],
        "chapters": [{"id": "20", "parent_id": "10", "title": "Chapter"}],
        "activities": [
            {
                "id": "30",
                "parent_id": "20",
                "title": "Lesson",
                "content": "Body",
                "activity_type": "dynamic_page",
            }
        ],
        "users": [],
        "enrollments": [],
    }

    plan = module.build_plan(document, 7)

    assert plan["courses"][0]["body"]["source_wordpress_id"] == "10"
    chapter = plan["courses"][0]["chapters"][0]
    assert chapter["body"]["course_id"] == "$course[10].id"
    assert chapter["activities"][0]["body"]["chapter_id"] == "$chapter[20].id"
    assert chapter["activities"][0]["body"]["published"] is False
