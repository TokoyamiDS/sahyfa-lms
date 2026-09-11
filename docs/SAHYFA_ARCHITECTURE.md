# Sahyfa Architecture

Sahyfa is a customized LearnHouse fork for migrating the existing Persian RTL LMS.

## Runtime

- `apps/web`: Next.js App Router, React, TypeScript, Tailwind CSS, and TipTap.
- `apps/api`: FastAPI, SQLModel, Alembic, and PostgreSQL.
- `apps/collab`: Hocuspocus and Yjs for collaborative editing.
- PostgreSQL: system of record, with `pgvector` enabled for future search and AI features.
- Redis: cache, sessions, and background coordination.
- S3-compatible storage: MinIO locally and object storage in production.

The frontend remains React-based. The API remains Python because LearnHouse's existing
course, assignment, certification, migration, and authorization boundaries are already
implemented there. New integrations should be added behind API services rather than by
introducing a second application backend.

## Fork boundaries

Sahyfa-specific changes belong in these areas:

- `apps/web`: Persian RTL layout, fonts, Jalali dates, and Sahyfa branding.
- `apps/api/src`: ZarinPal/Jibit payment adapters, SMS adapters, and migration endpoints.
- `apps/api/migrations`: Sahyfa-owned schema changes only.
- `scripts/sahyfa`: repeatable WordPress/Tutor LMS extraction and LearnHouse import tooling.

Do not modify upstream behavior for one-off migration logic. Keep import transforms and
legacy ID mappings in `scripts/sahyfa` so they can be rerun against a staging database.

## Version policy

The fork tracks the upstream `dev` branch baseline. Dependency upgrades must be made in
small, tested commits and must preserve the current major versions:

- Next.js 16
- React 19
- Tailwind CSS 4
- TypeScript 6
- PostgreSQL 16 in the application stack

The local development database intentionally uses PostgreSQL with `pgvector`, not SQLite.

## Migration phases

1. Boot the fork and verify PostgreSQL, Redis, and object storage.
2. Add Persian RTL/Jalali foundations and Sahyfa branding.
3. Build a read-only WordPress/Tutor extractor and ID mapping tables.
4. Import one representative course, then all courses, activities, users, and enrollments.
5. Add ZarinPal/Jibit payment adapters and access-grant workflows.
6. Run parallel QA and cut over after payment and enrollment parity is verified.
