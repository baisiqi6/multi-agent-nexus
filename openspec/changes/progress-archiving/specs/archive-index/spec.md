## ADDED Requirements

### Requirement: Active directory keeps a stable pointer to the archive
The system SHALL leave a lightweight stub file in the original task directory after archiving, so existing links and documentation references continue to resolve.

#### Scenario: Stub points to archive
- **WHEN** a phase has been archived
- **THEN** `tasks/<phase-id>/README.md` exists and contains a relative link to `../../archive/<phase-id>/`
- **AND** the stub includes the closeout event id and archived timestamp for audit purposes

### Requirement: Archive index is machine-readable
The system SHALL generate an `INDEX.md` inside each archive directory that records provenance and enables programmatic rediscovery.

#### Scenario: Index contains required fields
- **WHEN** the archive command succeeds
- **THEN** `archive/<phase-id>/INDEX.md` includes the fields: `original_path`, `archive_path`, `workspace_id`, `task_id`, `closeout_event_id`, `closed_at`, `commit_sha`
- **AND** the index is valid Markdown with a YAML front-matter block or key-value list parseable by simple regex

### Requirement: Archive pointer survives directory renames
The system SHALL use relative paths in the stub so that the repository can be moved or cloned elsewhere without breaking the pointer.

#### Scenario: Relative link in stub
- **WHEN** the stub `tasks/<phase-id>/README.md` is generated
- **THEN** all links to the archive use paths relative to `tasks/<phase-id>/README.md`
- **AND** no absolute filesystem paths are written
