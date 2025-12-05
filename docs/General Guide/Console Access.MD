---
route: console-access
allow_guest: 1
published: 1
---

### How to get Server Access:

For `f7-mumbai.frappe.cloud`

1. Open **User SSH Certificate List**.
2. Create User SSH Certificate for the server you want access to, in this case `f7-mumbai.frappe.cloud`.
3. Fill details such as server name, reason for accessing the server, validity period for eg. 6 Hrs.

![Certificate Details](https://frappecloud.com/files/Screenshot%202022-11-15%20at%2012.54.12%20PM.png)

4. Click on **Copy Certificate Details**, it will copy the certificate in the clipboard and then paste it in your terminal.
5. Now click on **Copy SSH Command**, it will copy the SSH command in the clipboard and then paste it in your terminal.
6. You should be able to access the frappe user in `f7-mumbai.frappe.cloud` server.


### How to get Bench Console Access:

For `bench-0032-000631-f1`


For old style benches:
```sh
$ ssh f1.frappe.cloud -l frappe

frappe@f1:~$ docker container ls | grep bench-0032-000631-f1 | grep web
```

For new style benches:
```sh
$ ssh f1.frappe.cloud -l frappe

frappe@f1:~$ docker container ls | grep bench-0032-000631-f1
```

This would show an output similar to

```sh
ad8b1b6ac859 registry.frappe.cloud/production/frappe.cloud/bench-0032:deploy-0032-000631          "/home/frappe/frappe…" 12 days ago  Up 12 days  8000/tcp bench-0032-000631-f1_web.1.dwwpbeewfsxsakcsl3o3anyxp
```

The first string in the output is the container ID and you can use it with docker exec. e.g.

```sh
frappe@f1:~$ docker exec -it ad8b1b6ac859 bash
```

Which will drop you in the sites directory of the bench

```sh
frappe@ad8b1b6ac859:~/frappe-bench/sites$
frappe@ad8b1b6ac859:~/frappe-bench/sites$ cd ..
frappe@ad8b1b6ac859:~/frappe-bench$ ls
apps config env logs sites
```