#!/usr/bin/env bash
set -e
DATE=$(date +%F)
bucket="lightsail-backups"
file="dealbot.db"
aws s3 cp $file s3://$bucket/$DATE/$file 