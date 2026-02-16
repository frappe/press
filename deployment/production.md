# Production

Since production is running a custom setup with multiple apps and a fork of
Frappe, we have to be very careful while updating the code. Always make sure to
test your changes on staging.frappe.cloud (You'll find it on Frappe Cloud!)
before deploying to production.

> Never do `bench update` on production. Always manually pull each app's repo and run necessary commands.

## Updating Press on Production

```sh
cd ~/frappe-bench/apps/press
```

```sh
git pull origin master
```

If migrate is required

```sh
bench migrate
```

If web workers need to be restarted, **DON'T** run `bench restart --web`. Do this instead:

```sh
sudo supervisorctl signal SIGHUP frappe-bench-web:
```

This will tell Gunicorn to reload the application without restarting the whole web worker process, which is much faster and less disruptive.

If background workers need to be restarted, **DON'T** run `bench restart`. (Since this will also restart web workers, which we don't want.) Do this instead:

```sh
sudo supervisorctl restart frappe-bench-workers:
```

Usually this is what you need. Since we have some frequent time consuming jobs in a separate worker group, we often want to avoid restarting that group. If, your code change affects that group, you can also do:

```sh
sudo supervisorctl restart frappe-bench-chill-workers:
```

You can see what all worker groups you have by running:

```sh
sudo supervisorctl status all
```

## Frappe Fork

Production is currently running a fork of Frappe due to various reasons. This is not ideal, but it is what it is.

The fork is available [here](https://github.com/balamurali27/frappe/tree/fc-prod)

# Updating Frappe on Production

Firsly, you need to update the fork by creating a pull request from the main [Frappe](https://github.com/frappe/frappe) repo to the fork. Once the PR is merged, you can pull the changes on production.

```sh
cd ~/frappe-bench/apps/frappe
```

```sh
git pull origin fc-prod
```

Now, you can run the same commands as mentioned in the previous section to migrate and restart workers if needed. Usually, you need to restart all workers since Frappe is the core framework and any change in it can affect all apps.
