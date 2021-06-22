docker run -d --name registry-ui \
  --restart always \
  --net container:registry \
  -e REGISTRY_TITLE="Frappe Cloud Registry" \
  -e NGINX_PROXY_PASS_URL=http://127.0.0.1:5000 \
  -e DELETE_IMAGES=true \
  -e SINGLE_REGISTRY=true \
  joxit/docker-registry-ui:latest
