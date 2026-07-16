#!/usr/bin/env bash
# P9-3C1 P2 Inert Production Controller — thin root/run-id entrypoint.
#
# Validates EUID, fixed paths, run-id shape, then execs the installed Python
# controller with original argv. No sourceable mode, eval, or env override.
# Use: sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh <subcommand> ...

set -euo pipefail

readonly EXPECTED_EUID=0
readonly EXPECTED_PYTHON='/opt/multinexus/.venv/bin/python'
readonly EXPECTED_CONTROLLER='/opt/multinexus/scripts/p9_3c1_controller.py'

if [[ "${EUID:-$(id -u)}" -ne "${EXPECTED_EUID}" ]]; then
    printf 'p9-3c1-production-verify.sh: must run as root (EUID 0), got %s\n' "${EUID:-unknown}" >&2
    exit 1
fi

if [[ $# -lt 1 ]]; then
    printf 'usage: p9-3c1-production-verify.sh <prepare|preflight|status|run|cleanup> ...\n' >&2
    exit 2
fi

_subcommand="$1"
shift

# Validate run-id from arguments: --run-id must appear exactly once with a
# non-empty value matching the production run-id regex.
_run_id=''
while [[ $# -gt 0 ]]; do
    case "$1" in
        --run-id)
            if [[ -n "${_run_id}" ]]; then
                printf 'p9-3c1-production-verify.sh: --run-id specified more than once\n' >&2
                exit 2
            fi
            if [[ $# -lt 2 ]]; then
                printf 'p9-3c1-production-verify.sh: --run-id requires a value\n' >&2
                exit 2
            fi
            _run_id="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

if [[ -z "${_run_id}" ]]; then
    printf 'p9-3c1-production-verify.sh: --run-id is required\n' >&2
    exit 2
fi

# Exact regex from plan: p9-3c1-prod-YYYYMMDDtHHMMSSz-hex8
if ! [[ "${_run_id}" =~ ^p9-3c1-prod-[0-9]{8}t[0-9]{6}z-[a-f0-9]{8}$ ]]; then
    printf 'p9-3c1-production-verify.sh: invalid run-id format: %s\n' "${_run_id}" >&2
    exit 2
fi

if [[ ${#_run_id} -gt 42 ]]; then
    printf 'p9-3c1-production-verify.sh: run-id exceeds 42 bytes: %s\n' "${_run_id}" >&2
    exit 2
fi

if [[ ! -x "${EXPECTED_PYTHON}" ]]; then
    printf 'p9-3c1-production-verify.sh: Python not found at %s\n' "${EXPECTED_PYTHON}" >&2
    exit 1
fi

if [[ ! -f "${EXPECTED_CONTROLLER}" ]]; then
    printf 'p9-3c1-production-verify.sh: controller not found at %s\n' "${EXPECTED_CONTROLLER}" >&2
    exit 1
fi

exec "${EXPECTED_PYTHON}" "${EXPECTED_CONTROLLER}" "${_subcommand}" "$@"
