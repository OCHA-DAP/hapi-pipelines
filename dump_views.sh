#!/bin/bash

printf -v now '%(%Y-%m-%d %H:%M:%S)T\n' -1
echo "Started at $now"

mkdir -p database/csv

tables=$(docker exec -t postgres-container psql -t -U postgres -d hapi -c \
  "select table_name from INFORMATION_SCHEMA.views WHERE table_schema = ANY (current_schemas(false))")

for table in $tables
do
  table=${table::-1}
  if [[ -z "$table" ]]; then
    continue
  fi

  echo "Saving $table"

  docker exec -t postgres-container psql -U postgres -d hapi -c \
    "\copy (select * from ${table}_view) TO STDOUT (FORMAT csv, DELIMITER ',',  HEADER);" \
    | tee \
    >(gzip > database/csv/${table}.csv.gz) \
    >(md5sum | awk '{print $1}' > database/csv/${table}.hash) \
    >/dev/null
done

docker exec -t postgres-container pg_dump -U postgres -Fc hapi -f hapi_db.pg_restore
docker cp postgres-container:/hapi_db.pg_restore database/hapi_db.pg_restore

printf -v now '%(%Y-%m-%d %H:%M:%S)T\n' -1
echo "Ended at $now"
