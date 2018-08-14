#!/bin/bash
echo "starting..."
./scripts/wait_for_it.sh $POLYSWARM_HOST:$POLYSWARM_PORT -t 0
arbiter
