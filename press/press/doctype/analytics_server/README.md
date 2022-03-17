Added following locations to NGINX config on frappecloud.com

Some adblockers don't seem to like third party domains and "plausible.js"

```
location = /js/script.js {
	proxy_pass https://analytics.frappe.cloud/js/plausible.js;
	proxy_buffering on;

	proxy_cache jscache;
	proxy_cache_valid 200 6h;
	proxy_cache_use_stale updating error timeout invalid_header http_500;

	proxy_set_header Host analytics.frappe.cloud;
	proxy_ssl_name analytics.frappe.cloud;
	proxy_ssl_server_name on;
	proxy_ssl_session_reuse off;

	proxy_ssl_protocols TLSv1.3;

}

location = /api/event {
	proxy_pass https://analytics.frappe.cloud/api/event;
	proxy_buffering on;
	proxy_http_version 1.1;

	proxy_set_header X-Forwarded-For	$proxy_add_x_forwarded_for;
	proxy_set_header X-Forwarded-Proto	$scheme;
	proxy_set_header X-Forwarded-Host	$host;

	proxy_set_header Host analytics.frappe.cloud;
	proxy_ssl_name analytics.frappe.cloud;
	proxy_ssl_server_name on;
	proxy_ssl_session_reuse off;

	proxy_ssl_protocols TLSv1.3;
}
```

Also added a cache zone for caching the plausible script

```
proxy_cache_path /var/cache/nginx/jscache levels=1:2 keys_zone=jscache:100m inactive=30d  use_temp_path=off max_size=100m;
```
