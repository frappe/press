```
docker run -it -p 127.0.0.1:8021:8080 \
    -v "/home/frappe/repos:/home/coder/project:ro" \
    --env PASSWORD=3ZRoh4XT7MhscBAn2dcdDMQWt8HoWpZF \
    -d --name codeserver --restart=always \
    codercom/code-server:latest \
    --disable-telemetry --proxy-domain code.staging.frappe.cloud --verbose /home/coder/project
```

```
server {
    listen 80;
    server_name code.staging.frappe.cloud;
    location / {
        proxy_pass                          http://127.0.0.1:8021;
        proxy_http_version 1.1;
        proxy_set_header  Upgrade           $http_upgrade;
        proxy_set_header  Connection        'Upgrade';
        proxy_set_header  Host              $http_host;
        proxy_set_header  X-Real-IP         $remote_addr;
        proxy_set_header  X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header  X-Forwarded-Proto $scheme;
    }
}
```