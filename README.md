<div align="center" markdown="1">

<img src="https://frappe.io/files/Group%202%20(1).png" alt="Press logo" width="80"/>
<h1>Press</h1>

**Full Service Cloud Hosting For The Frappe Stack - Powers Frappe Cloud**

[![codecov](https://codecov.io/gh/frappe/press/branch/master/graph/badge.svg?token=0puvH0jUx9)](https://codecov.io/gh/frappe/press)
[![unittests](https://github.com/frappe/press/actions/workflows/main.yaml/badge.svg)](https://github.com/frappe/press/actions/workflows/main.yaml)

</div>

<div align="center">
	<img width="889" alt="Managed press" src="https://github.com/user-attachments/assets/2675e828-d5ed-4527-a038-7742a5cfa3db" />
</div>
<br />
<div align="center">
	<a href="https://frappe.io/press">Website</a>
	-
	<a href="https://docs.frappe.io/cloud/">Documentation</a>
</div>

## Press

Press is a 100% open-source cloud hosting for the Frappe stack.

### Motivation

We originally hosted our customer sites on an internal cloud platform called "Central," designed to automate creating and hosting sites when customers signed up on our website. Central was primarily built to host ERPNext, our flagship product. However, as our customers' needs evolved, they began requesting the ability to host custom applications, a feature that was not a priority in Central.

Additionally, customers lacked full control over their servers—no SSH access, no ability to manage updates, and limited flexibility in interacting with their environment. This led us to launch Frappe Cloud, to build a self-serve cloud platform that would empower our customers with complete control over their hosting experience.

### Key Features

- **Multitenancy Made Easy**: Press simplifies multi-tenancy by enabling multiple sites on a single platform, each with its app version, allowing independent updates and minimal downtime, even for large sites.
- **Dashboard**: The dashboard provides a centralized interface to manage apps, servers, sites, billing, backups, and updates, offering real-time insights and streamlined control of complex operations.

- **Permissions**: Granular access controls let team owners manage roles and resources efficiently, ensuring users have access only to relevant information and actions for their roles.

- **Simplified Management**: Press streamlines site management with automated backups, real-time monitoring, role-based access, and easy scaling, making it ideal for growing Frappe environments.

- **Billing**: Automated billing supports daily or monthly subscriptions, flexible payment methods, wallet credits, and ERP integration, simplifying customer invoicing and payments.

- **Marketplace**: The marketplace allows developers to list apps with flexible pricing models, ensures compatibility checks, and provides a streamlined system for sales and payouts.

<details>
  <summary>Screenshots</summary>

![Dashboard](https://github.com/user-attachments/assets/1904fa3e-39aa-4151-8276-d3cc622ed582)
![Permissions](https://github.com/user-attachments/assets/60da6b5e-8f48-4483-99cf-67886ccc8bd6)
![Bench Group Update](https://github.com/user-attachments/assets/2be6b0ee-084d-4949-8d13-218b5a218d3d)
![Marketplace](https://github.com/user-attachments/assets/2f325737-7929-485d-a670-549f986fd07e)

</details>

### Under the Hood

- [**Frappe Framework**](https://github.com/frappe/frappe): A full-stack web application framework written in Python and Javascript. The framework provides a robust foundation for building web applications, including a database abstraction layer, user authentication, and a REST API.

- [**Frappe UI**](https://github.com/frappe/frappe-ui): A Vue-based UI library, to provide a modern user interface. The Frappe UI library provides a variety of components that can be used to build single-page applications on top of the Frappe Framework.

- [**Agent**](https://github.com/frappe/agent): A flask app designed to work along with Press. It provides a CLI interface for Press to communicate with the sites and benches.

- [**Docker**](https://www.docker.com): An open-source platform that enables developers to build, package, and deploy applications in lightweight, portable containers.

- [**Ansible**](https://www.ansible.com): An open-source IT automation tool that simplifies the management, configuration, and deployment of systems and applications.

## Setup

To self host or to setup Press locally follow the steps in the [Local Development Environment Setup Guide](https://docs.frappe.io/cloud/local-fc-setup).

### Migrate to Frappe Cloud

If you are planning to migrate your site to Frappe Cloud, please refer to [this YouTube video](https://www.youtube.com/watch?v=Xb9QHnUrIEk)

### Pre-commit

There's a [pre-commit](https://pre-commit.com/) hook included in the repo. You can set it up by doing

```bash
pip install pre-commit
pre-commit install
```
## Learn and connect

- [Telegram Public Group](https://t.me/frappecloud)
- [Discuss Forum](https://discuss.frappe.io/c/frappe-cloud/77)
- [Documentation](https://docs.frappe.io/cloud)

<br/>
<br/>
<div align="center" style="padding-top: 0.75rem;">
	<a href="https://frappe.io" target="_blank">
		<picture>
			<source media="(prefers-color-scheme: dark)" srcset="https://frappe.io/files/Frappe-white.png">
			<img src="https://frappe.io/files/Frappe-black.png" alt="Frappe Technologies" height="28"/>
		</picture>
	</a>
</div>
