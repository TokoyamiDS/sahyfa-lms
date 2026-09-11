# Sahyfa Migration Tools

These tools are intentionally read-only against the WordPress database.

## Extract

Set the database connection values and run:

```powershell
$env:SAHYFA_WP_DB_NAME = "sahyfair_sahyfa1403"
$env:SAHYFA_WP_DB_USER = "root"
$env:SAHYFA_WP_DB_HOST = "127.0.0.1"
python scripts/sahyfa/extract_tutor.py --output .sahyfa/migration.json
```

For a remote database, set `SAHYFA_WP_DB_PASSWORD` or pass `--password` through a
secure environment variable. The extractor invokes the MySQL client in batch mode;
it does not modify WordPress or LearnHouse.

The JSON output is an intermediate artifact. It preserves WordPress IDs and raw
metadata so import mappings can be rerun without querying the production site again.

## Migration shape

- `courses`: published `courses` posts.
- `chapters`: Tutor `topics` posts, retained with their WordPress parent IDs.
- `activities`: `lesson` and `cb-lesson` posts with inferred video/document/page type.
- `quizzes`: Tutor quiz posts and their raw metadata.
- `users`: WordPress users and roles.
- `enrollments`: Tutor enrollment posts with status and order/product metadata.

The next importer will consume this artifact and call LearnHouse's API only after the
mapping has been reviewed.
