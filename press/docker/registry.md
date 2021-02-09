1. Start registry with

    ```shell
    docker run -d -p 5000:5000 --restart=always --name registry registry:2
    ```

1. Create `.htpasswd` file with 

    ```
    htpasswd -Bbn user password > registry.htpasswd
    ```

1. Start Registry UI with
    ```
    docker run -d --name registry-ui -p 6000:80 -e REGISTRY_URL=https://registry.frappe.cloud -e DELETE_IMAGES=true -e REGISTRY_TITLE="My registry" joxit/docker-registry-ui:static
    ```

1. Use registry.conf as NGINX config