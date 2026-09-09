#!/usr/bin/env bash
set -euo pipefail

remote="${1:-origin}"
branch="${2:-market-data}"
head_ref="refs/heads/${branch}"
remote_ref="refs/remotes/${remote}/${branch}"

remote_listing=""
listing_ok=0
for attempt in 1 2 3; do
  if remote_listing=$(git ls-remote --heads "${remote}" "${head_ref}"); then
    listing_ok=1
    break
  fi
  echo "::warning::Could not query ${remote}/${branch} (attempt ${attempt}/3)"
  sleep $((attempt * 2))
done

if [[ "${listing_ok}" != "1" ]]; then
  echo "::error::Unable to determine whether ${remote}/${branch} exists after 3 attempts"
  exit 1
fi

if [[ -z "${remote_listing}" ]]; then
  echo "::notice::${remote}/${branch} does not exist yet; using cold-start state"
  exit 0
fi

for attempt in 1 2 3; do
  if git fetch --no-tags "${remote}" "${head_ref}:${remote_ref}"; then
    echo "Fetched ${remote}/${branch}"
    exit 0
  fi
  echo "::warning::Could not fetch ${remote}/${branch} (attempt ${attempt}/3)"
  sleep $((attempt * 2))
done

echo "::error::${remote}/${branch} exists but could not be fetched after 3 attempts"
exit 1
