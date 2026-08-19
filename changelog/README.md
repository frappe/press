# changelog

The public changelog for Frappe Cloud, at
[cloud.frappe.io/releases](https://cloud.frappe.io/releases). It is an
[Astro](https://astro.build) site, separate from the dashboard.

A release is one Markdown file in `src/content/releases/`. The file name is the
version, with an underscore for the dot. Version 1.0 is `1_0.md`.

```bash
cd changelog
yarn install
yarn dev      # development server
yarn build    # writes to press/www/releases, which Frappe serves
```

Needs Node 22.12 or later. The build output is not in git.
