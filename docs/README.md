# docs

Internal documentation for Frappe Cloud, built with
[VitePress](https://vitepress.dev). These pages explain how the code works.
User documentation lives at [docs.frappe.io/cloud](https://docs.frappe.io/cloud).

- `architecture/` — how the parts of Frappe Cloud fit together
- `code/` — one directory for each area: agent, guards, site update, testing, webhook
- `.vitepress/` — site configuration, theme, and the GitHub code embed plugin

Run the development server from the repository root:

```bash
yarn docs:dev
```

Add a page as a Markdown file under `architecture/` or `code/`. The
`vitepress-sidebar` plugin builds the sidebar from the directory, so a new file
appears without a change to the configuration.
