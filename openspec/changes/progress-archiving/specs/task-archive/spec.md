## ADDED Requirements

### Requirement: Archive command migrates closed phase artifacts
The system SHALL provide a CLI command that, given a workspace and a closed phase id, copies the phase's task directory into an archive location and leaves a stable pointer in the original location.

#### Scenario: Archive a closed phase
- **WHEN** the operator runs `coordinate task archive <workspace-id> --task-id phase-8.4.2`
- **THEN** the system copies all files from `tasks/phase-8.4.2/` to `archive/phase-8.4.2/`
- **AND** creates `archive/phase-8.4.2/INDEX.md` recording the original path, closeout event id, closed timestamp, and relevant commit SHA
- **AND** replaces `tasks/phase-8.4.2/` contents with a `README.md` stub that links to the archive directory
- **AND** updates `current/closeout-packet.md` (or equivalent active packet) to reference the archived location if it previously pointed to the task directory

### Requirement: Archive refuses to archive non-closed phases
The system SHALL reject the archive command unless the task mirror reports the phase as `closed` or `done`.

#### Scenario: Attempt to archive a running phase
- **WHEN** the operator runs `coordinate task archive <workspace-id> --task-id phase-8.8`
- **AND** the task mirror phase is `running`
- **THEN** the command fails with a clear error and no files are moved or copied

### Requirement: Archive is idempotent
The system SHALL allow the archive command to run multiple times for the same closed phase without creating duplicate archive entries or corrupting the stub.

#### Scenario: Re-archive the same phase
- **WHEN** the operator runs `coordinate task archive` for a phase that is already archived
- **THEN** the command succeeds and the existing archive directory remains unchanged
- **AND** the stub in `tasks/<phase-id>/README.md` continues to point to the same archive location

#### Scenario: Partial archive state is rejected
- **WHEN** the operator runs `coordinate task archive` for a phase where only the archive directory or only the archive stub exists
- **THEN** the command fails with a clear partial-state error
- **AND** the source task directory remains untouched

### Requirement: Dry-run previews the exact archive effects
The system SHALL support a dry-run mode that computes the archive target paths and link rewrites without modifying the filesystem.

#### Scenario: Dry-run a closed phase
- **WHEN** the operator runs `coordinate task archive <workspace-id> --task-id phase-8.4.2 --dry-run`
- **AND** `current/*.md` contains one file that links to `tasks/phase-8.4.2/plan.md` and one unrelated Markdown file
- **THEN** the command reports the source task directory, archive directory, stub path, and only the `current/*.md` file whose contents would change
- **AND** no archive directory, stub, index, or rewritten packet is written

### Requirement: Harness plan-path readers resolve archived task stubs
The system SHALL allow harness plan-path readers that encounter a task stub to resolve that task's plan from the archive when the original task directory contains only a stub.

#### Scenario: Resolve archived plan path
- **WHEN** `harnessctl`, `build_harness_state.py`, or `workflow_transition.py` needs the plan for a task
- **AND** `tasks/<phase-id>/plan.md` is absent
- **AND** `tasks/<phase-id>/README.md` points to `archive/<phase-id>/`
- **THEN** the reader resolves the plan path to `archive/<phase-id>/plan.md`
- **AND** `validate_checklist.py` remains unchanged because it only validates checklist JSON schema

### Requirement: Archive preserves file content and metadata
The system SHALL copy into the archive every file present in the source task directory, without altering content, excluding only runtime/byproducts that are gitignored (e.g. `:memory:*`, logs, local DB shards). Archiving is a faithful copy of the task's tracked artifacts — it does not filter by extension. Binary assets that an operator wants preserved alongside should live in the task dir at archive time; anything not meant to be archived should not be in the task dir to begin with.

#### Scenario: Archive contains all original files
- **WHEN** the archive command succeeds
- **THEN** every file in `tasks/<phase-id>/` before archiving has an equivalent in `archive/<phase-id>/` with identical content
- **AND** `INDEX.md` is added but no original file is removed from the archive copy
- **AND** gitignored runtime byproducts (if any are present) are skipped with a logged note, not copied
