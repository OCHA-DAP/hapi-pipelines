#!/bin/bash

printf -v now '%(%Y-%m-%d %H:%M:%S)T\n' -1
echo "Started at $now"

mkdir -p database/csv

views=$(docker exec -i postgres-container psql -t -U postgres -d hapi -c \
  "select table_name from INFORMATION_SCHEMA.views WHERE table_schema = ANY (current_schemas(false))")

for view in $views
do
  if [[ -z "$view" ]]; then
    continue
  fi

  echo "Saving $view"

  docker exec -t postgres-container psql -U postgres -d hapi -c \
    "\copy (select * from ${view}) TO STDOUT (FORMAT csv, DELIMITER ',',  HEADER);" \
    | tee \
    >(gzip > database/csv/${view}.csv.gz) \
    >(md5sum | awk '{print $1}' > database/csv/${view}.hash) \
    >/dev/null
done

docker exec -t postgres-container pg_dump -U postgres -Fc -Z 0 hapi \
    | unxz -z -9 > database/hapi_db.pg_restore.xz
docker cp postgres-container:/hapi_db.pg_restore.xz database/hapi_db.pg_restore.xz

printf -v now '%(%Y-%m-%d %H:%M:%S)T\n' -1
echo "Ended at $now"
