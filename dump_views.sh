#!/bin/bash

today=$(date +%Y%m%d-%H%M%S)

echo "Started at $today"

mkdir -p csv_export

for table in location admin1 admin2 population operational_presence humanitarian_needs
do
  echo "Saving $table"
  docker exec -t postgres-container psql -U postgres -d hapi -c "\copy (select * from ${table}_view) TO STDOUT (FORMAT csv, DELIMITER ',',  HEADER);" | tee >(gzip > csv_export/${table}.csv.gz) >(md5sum > csv_export/${table}.hash) >/dev/null
done

# end
end=$(date +%Y%m%d-%H%M%S)

echo "Ended at $end."
