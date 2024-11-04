```
docker build -t your_image_name .

docker run -d \
  -p 8080:8080 \
  -p 8443:8443 \
  -p 5901:5901 \
  -e PASSWORD="your_code_server_password" \
  -e VNC_PASSWORD="your_vnc_password" \
  your_image_name

```