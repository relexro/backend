#!/bin/bash
for func in $(gcloud functions list --project=relexro --regions=europe-west3 --format="value(name)" | grep "relex-backend-"); do
  echo "Deleting function: $func"
  gcloud functions delete $func --project=relexro --region=europe-west3 --quiet
done
