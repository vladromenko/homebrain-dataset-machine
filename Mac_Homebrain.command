#!/bin/bash
set -euo pipefail
homebrain_host="${HOMEBRAIN_HOST:?Set HOMEBRAIN_HOST to the Jetson SSH address}"
homebrain_user="${HOMEBRAIN_USER:?Set HOMEBRAIN_USER to the Jetson SSH user}"
homebrain_remote_dir="${HOMEBRAIN_REMOTE_DIR:-/srv/homebrain-dataset-machine}"
printf -v homebrain_remote_start '%q start' "$homebrain_remote_dir/homebrain.sh"
echo 'Keep this window open. The UI will be at http://localhost:8090'
ssh "$homebrain_user@$homebrain_host" "$homebrain_remote_start"
(sleep 2; open http://localhost:8090) &
exec ssh -N -o ExitOnForwardFailure=yes -L 8090:127.0.0.1:8090 -L 8020:127.0.0.1:8020 "$homebrain_user@$homebrain_host"
