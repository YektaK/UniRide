#!/bin/bash
cd /home/z/my-project
rm -rf .next
while true; do
  bun run dev 2>&1 | tee dev.log
  echo "Server died, restarting in 2s..."
  sleep 2
done
