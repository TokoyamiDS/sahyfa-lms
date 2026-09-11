"""Build a reviewable LearnHouse API import plan from an extractor artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def activity_payload(activity: dict, chapter_id: str) -> dict:
    activity_type = activity["activity_type"]
    if activity_type == "external_video":
        subtype = "SUBTYPE_VIDEO_YOUTUBE"
    elif activity_type == "embed":
        subtype = "SUBTYPE_DYNAMIC_EMBED"
    else:
        subtype = "SUBTYPE_DYNAMIC_PAGE"

    return {
        "name": activity["title"],
        "chapter_id": chapter_id,
        "activity_type": "TYPE_VIDEO" if activity_type == "external_video" else "TYPE_DYNAMIC",
        "activity_sub_type": subtype,
        "content": {
            "source_wordpress_id": activity["id"],
            "html": activity.get("content", ""),
            "raw_meta": activity.get("meta", {}),
        },
        "published": False,
        "source_wordpress_id": activity["id"],
    }


def build_plan(document: dict, org_id: int) -> dict:
    courses = []
    chapters_by_parent: dict[str, list[dict]] = {}
    for chapter in document["chapters"]:
        chapters_by_parent.setdefault(str(chapter["parent_id"]), []).append(chapter)

    activities_by_parent: dict[str, list[dict]] = {}
    for activity in document["activities"]:
        activities_by_parent.setdefault(str(activity["parent_id"]), []).append(activity)

    for course in document["courses"]:
        course_id = str(course["id"])
        course_plan = {
            "method": "POST",
            "path": "/api/v1/courses/",
            "query": {"org_id": org_id},
            "body": {
                "name": course["title"],
                "description": course.get("content", ""),
                "published": False,
                "source_wordpress_id": course["id"],
            },
            "source_wordpress_id": course["id"],
            "chapters": [],
        }
        for chapter in chapters_by_parent.get(course_id, []):
            chapter_plan = {
                "method": "POST",
                "path": "/api/v1/chapters/",
                "body": {
                    "name": chapter["title"],
                    "course_id": f"$course[{course_id}].id",
                    "org_id": org_id,
                    "source_wordpress_id": chapter["id"],
                },
                "source_wordpress_id": chapter["id"],
                "activities": [],
            }
            for activity in activities_by_parent.get(str(chapter["id"]), []):
                chapter_plan["activities"].append(
                    {
                        "method": "POST",
                        "path": "/api/v1/activities/",
                        "body": activity_payload(activity, f"$chapter[{chapter['id']}].id"),
                        "source_wordpress_id": activity["id"],
                    }
                )
            course_plan["chapters"].append(chapter_plan)
        courses.append(course_plan)

    return {
        "schema_version": 1,
        "mode": "review_only",
        "org_id": org_id,
        "source_schema_version": document.get("schema_version"),
        "courses": courses,
        "users": [
            {"source_wordpress_id": user["id"], "email": user["email"], "username": user["login"]}
            for user in document["users"]
        ],
        "enrollment_count": len(document["enrollments"]),
        "notes": [
            "All content is unpublished until reviewed.",
            "$course[...] and $chapter[...] references must be resolved from create responses.",
            "Payment and enrollment grants are intentionally not executed by this plan.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--org-id", type=int, required=True)
    args = parser.parse_args()
    document = json.loads(args.input.read_text(encoding="utf-8"))
    plan = build_plan(document, args.org_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"courses": len(plan["courses"]), "enrollments": plan["enrollment_count"]}))


if __name__ == "__main__":
    main()
