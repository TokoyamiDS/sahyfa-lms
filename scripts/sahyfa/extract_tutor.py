"""Extract the WordPress/Tutor data needed for a LearnHouse migration.

The extractor is deliberately read-only and uses the installed MySQL CLI instead of
adding a database driver to the application runtime. Raw metadata is retained because
Tutor and Elementor store some values as PHP-serialized strings.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


POST_TYPES = ("courses", "topics", "lesson", "cb-lesson", "tutor_quiz", "tutor_certificate")


def mysql_query(query: str, args: argparse.Namespace) -> list[dict[str, str]]:
    command = [
        args.mysql,
        "--batch",
        "--raw",
        "--skip-column-names",
        "--default-character-set=utf8mb4",
        "--host",
        args.host,
        "--user",
        args.user,
        args.database,
        "--execute",
        query,
    ]
    env = os.environ.copy()
    if args.password:
        env["MYSQL_PWD"] = args.password

    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        env=env,
    )
    output = result.stdout.decode("utf-8", errors="replace")
    rows = csv.reader(output.splitlines(), delimiter="\t")
    return [dict(zip(args.columns, row, strict=False)) for row in rows]


def mysql_json_query(query: str, args: argparse.Namespace) -> list[dict[str, str]]:
    command = [
        args.mysql,
        "--batch",
        "--raw",
        "--skip-column-names",
        "--default-character-set=utf8mb4",
        "--host",
        args.host,
        "--user",
        args.user,
        args.database,
        "--execute",
        query,
    ]
    env = os.environ.copy()
    if args.password:
        env["MYSQL_PWD"] = args.password
    result = subprocess.run(command, check=True, capture_output=True, env=env)
    output = result.stdout.decode("utf-8", errors="replace")
    return [json.loads(line) for line in output.splitlines() if line.strip()]


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def extract_posts(args: argparse.Namespace) -> list[dict[str, str]]:
    types = ", ".join(sql_string(post_type) for post_type in POST_TYPES)
    return mysql_json_query(
        "SELECT JSON_OBJECT(" 
        "'id', ID, 'parent_id', post_parent, 'post_type', post_type, 'status', post_status, "
        "'title', post_title, 'content', post_content, 'created_at', post_date, 'updated_at', post_modified) "
        f"FROM {args.prefix}posts WHERE post_type IN ({types}) ORDER BY ID",
        args,
    )


def extract_meta(args: argparse.Namespace, post_ids: Iterable[str]) -> dict[str, dict[str, str]]:
    ids = [str(post_id) for post_id in post_ids]
    if not ids:
        return {}
    rows = mysql_json_query(
        f"SELECT JSON_OBJECT('post_id', post_id, 'meta_key', meta_key, 'meta_value', meta_value) "
        f"FROM {args.prefix}postmeta "
        f"WHERE post_id IN ({', '.join(ids)}) ORDER BY post_id, meta_id",
        args,
    )
    meta: dict[str, dict[str, str]] = defaultdict(dict)
    for row in rows:
        # Keep the first value for repeated keys. Tutor uses repeated metadata for
        # some relations, while the raw postmeta table is still available in backups.
        meta[row["post_id"]].setdefault(row["meta_key"], row["meta_value"])
    return dict(meta)


def extract_users(args: argparse.Namespace) -> list[dict[str, str]]:
    return mysql_json_query(
        f"SELECT JSON_OBJECT('id', ID, 'login', user_login, 'email', user_email, "
        f"'display_name', display_name, 'registered_at', user_registered) "
        f"FROM {args.prefix}users ORDER BY ID",
        args,
    )


def extract_enrollments(args: argparse.Namespace) -> list[dict[str, str]]:
    return mysql_json_query(
        f"SELECT JSON_OBJECT('id', ID, 'user_id', post_author, 'status', post_status, "
        f"'created_at', post_date, 'updated_at', post_modified, 'content', post_content) "
        f"FROM {args.prefix}posts WHERE post_type = 'tutor_enrolled' ORDER BY ID",
        args,
    )


def infer_activity(post: dict[str, str], meta: dict[str, str]) -> str:
    video = meta.get("_video", "")
    if "external_url" in video:
        return "external_video"
    if "shortcode" in video:
        return "embed"
    if post["post_type"] == "cb-lesson":
        return "bundle_lesson"
    return "dynamic_page"


def build_document(args: argparse.Namespace) -> dict:
    posts = extract_posts(args)
    metadata = extract_meta(args, (post["id"] for post in posts))
    by_type = defaultdict(list)
    for post in posts:
        by_type[post["post_type"]].append(post)

    courses = [
        {**post, "meta": metadata.get(post["id"], {})}
        for post in by_type["courses"]
        if post["status"] == "publish"
    ]
    chapters = [
        {**post, "meta": metadata.get(post["id"], {})}
        for post in by_type["topics"]
        if post["status"] == "publish"
    ]
    activities = [
        {
            **post,
            "meta": metadata.get(post["id"], {}),
            "activity_type": infer_activity(post, metadata.get(post["id"], {})),
        }
        for post_type in ("lesson", "cb-lesson")
        for post in by_type[post_type]
        if post["status"] == "publish"
    ]
    quizzes = [
        {**post, "meta": metadata.get(post["id"], {})}
        for post in by_type["tutor_quiz"]
        if post["status"] == "publish"
    ]

    return {
        "schema_version": 1,
        "source": {"database": args.database, "prefix": args.prefix},
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "courses": courses,
        "chapters": chapters,
        "activities": activities,
        "quizzes": quizzes,
        "certificates": by_type["tutor_certificate"],
        "users": extract_users(args),
        "enrollments": extract_enrollments(args),
        "counts": {
            "courses": len(courses),
            "chapters": len(chapters),
            "activities": len(activities),
            "quizzes": len(quizzes),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mysql", default=os.getenv("SAHYFA_MYSQL_BIN", "mysql"))
    parser.add_argument("--host", default=os.getenv("SAHYFA_WP_DB_HOST", "127.0.0.1"))
    parser.add_argument("--user", default=os.getenv("SAHYFA_WP_DB_USER", "root"))
    parser.add_argument("--password", default=os.getenv("SAHYFA_WP_DB_PASSWORD", ""))
    parser.add_argument("--database", default=os.getenv("SAHYFA_WP_DB_NAME", "wordpress"))
    parser.add_argument("--prefix", default=os.getenv("SAHYFA_WP_TABLE_PREFIX", "wp_"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    document = build_document(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(document["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
