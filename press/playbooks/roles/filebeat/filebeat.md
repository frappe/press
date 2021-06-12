If filebeat version on the newly setup server doesn't match the one on Elasticsearch server then you'll have to create the indexes manually.

1. Export the index payload from the newly setup server
```sh
filebeat export template > filebeat.template.json
```

2. Use the exported payload to create indexes (Replace `filebeat-version` with the appropriate version)
```sh
curl -XPUT -H 'Content-Type: application/json' http://localhost:9200/_template/filebeat-<filebeat-version> -d@filebeat.template.json
```