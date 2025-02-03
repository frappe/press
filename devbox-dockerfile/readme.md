### Create the volumes for persistence

```shell
docker volume create db-data

docker volume create home
```

### Build

```shell
docker build -t your_image_name .
```

### Run

6969 is for NOVNC \
8443 is for VSCode Server \
5901 is for Bare VNC Port

```
docker run -d \
  -p 6969:6969 \
  -p 8443:8443 \
  -p 5901:5901 \
  -v db-data:/var/lib/mysql \
  -v home:/home/frappe \
  -e PASSWORD="your_code_server_password" \
  -e VNC_PASSWORD="your_vnc_password" \
  your_image_name

```