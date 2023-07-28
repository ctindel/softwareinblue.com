#!/bin/bash

docker-buildx build --platform linux/arm64 -t sib:arm .
docker-compose -f docker-compose.yml up sib
