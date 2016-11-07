#!/bin/sh
exec ssh -i ~/.ssh/io-docker-gc -o StrictHostKeyChecking=no "$@"
