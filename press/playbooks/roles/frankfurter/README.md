# Guide to Setup Frankfurter
### Install Docker
#### Setup Docker Repository
```sh
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
```

#### Install Docker
 
```sh
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
Reference: https://docs.docker.com/engine/install/ubuntu/

#### Install Frankfurter

Copy `docker-compose.yml` from `/templates/`.

The compose configuration (`docker-compose.yml`) is prepared to match the `docker run` command from the docs

```sh
docker run -d -p 8080:8080 -e "DATABASE_URL=<postgres_url>"  --name frankfurter hakanensari/frankfurter
```
#### Start Frankfurter

```sh
docker compose up -d
```

### Setup TLS
#### Setup NGINX

Place a minimal server block in `/etc/nginx/conf.d`

```nginx
server {
	server_name frankfurter.frappe.cloud;
    location / {
        proxy_pass http://127.0.0.1:8080;
    }
}
```
#### Remove Default NGINX site
```sh
rm /etc/nginx/sites-enabled/default
rm /etc/nginx/sites-available/default
rm -rf /usr/share/nginx/html/
```

#### Setup Certbot

```sh
sudo python3 -m venv /opt/certbot/
sudo /opt/certbot/bin/pip install certbot
ln -s /opt/certbot/bin/certbot /usr/bin/certbot
certbot --nginx
```


#### Setup Certbot renewal cronjob
```sh
echo "0 0,12 * * * root /opt/certbot/bin/python -c 'import random; import time; time.sleep(random.random() * 3600)' && sudo certbot renew -q" | sudo tee -a /etc/crontab > /dev/null
```

Reference: https://certbot.eff.org/instructions?ws=nginx&os=ubuntufocal

#### Add frankfurter to blocked subdomains on FrappeCloud.com
https://frappecloud.com/app/blocked-domain/frankfurter

### Done
```sh
curl -s https://frankfurter.frappe.cloud/latest | jq
```

```json
{
  "amount": 1.0,
  "base": "EUR",
  "date": "2024-10-04",
  "rates": {
    "AUD": 1.6121,
    "CHF": 0.9394,
    "GBP": 0.83735,
    "INR": 92.61,
    "JPY": 161.69,
    "SGD": 1.4314,
    "USD": 1.1029,
    "ZAR": 19.2809
  }
}
```