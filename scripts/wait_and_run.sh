#!/bin/bash
echo "starting..."
./scripts/wait_for_it.sh $POLYSWARMD_HOST -t 0
./scripts/wait_for_it.sh $API_KEY_HOST -t 0

export API_KEY=$(./scripts/get_api_key.sh)
export POLYSWARMD_HOST="http://${POLYSWARMD_HOST}"

echo "arbiter API key: ${API_KEY}"

arbiter $*
