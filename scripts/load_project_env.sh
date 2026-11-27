#!/usr/bin/env bash

# Load the project's local environment file without replacing values that were
# explicitly set by the caller. The caller must define PROJECT_ROOT first.
hkc_load_project_env() {
  local project_root="${1:?missing project root}"
  local env_file="${HKC_SIM_ENV_FILE:-${project_root}/.env}"
  local line=""
  local name=""
  local allexport_was_set="false"
  local -A preserved=()

  if [[ ! -e "${env_file}" ]]; then
    if [[ -n "${HKC_SIM_ENV_FILE:-}" ]]; then
      echo "Environment file does not exist: ${env_file}" >&2
      return 1
    fi
    HKC_LOADED_ENV_FILE=""
    return 0
  fi
  [[ -f "${env_file}" ]] || {
    echo "Environment file is not a regular file: ${env_file}" >&2
    return 1
  }

  while IFS= read -r line || [[ -n "${line}" ]]; do
    if [[ "${line}" =~ ^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)= ]]; then
      name="${BASH_REMATCH[2]}"
      if [[ -v "${name}" ]]; then
        preserved["${name}"]="${!name}"
      fi
    fi
  done < "${env_file}"

  [[ "$-" == *a* ]] && allexport_was_set="true"
  set -a
  # shellcheck disable=SC1090
  source "${env_file}"
  [[ "${allexport_was_set}" == "true" ]] || set +a

  for name in "${!preserved[@]}"; do
    printf -v "${name}" '%s' "${preserved[${name}]}"
    export "${name}"
  done
  HKC_LOADED_ENV_FILE="${env_file}"
}
