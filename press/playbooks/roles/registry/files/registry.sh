docker run -d --name registry \
  --restart always \
  -e REGISTRY_LOG_ACCESSLOG_DISABLED=false \
  -e REGISTRY_HTTP_DEBUG_ADDR=":5001" \
  -e REGISTRY_HTTP_DEBUG_PROMETHEUS_ENABLED=true \
  -e REGISTRY_STORAGE_DELETE_ENABLED=true \
  -p 127.0.0.1:5000:5000 \
  -p 127.0.0.1:5001:5001 \
  -p 127.0.0.1:6000:80 \
  -v /home/frappe/registry/data:/var/lib/registry \
  registry:2
