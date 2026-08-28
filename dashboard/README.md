# Dashboard

Dashboard is the Vue application that customers of Frappe Cloud use. They have
no access to the desk, so this is where they manage their sites, apps, servers,
updates, and billing.

The application is built with these tools:

1. [Vue 3](https://vuejs.org/) — the JavaScript framework
2. [Frappe UI](https://github.com/frappe/frappe-ui) — the component library
3. [Tailwind CSS 3](https://tailwindcss.com/) — the styles
4. [Vite](https://vitejs.dev/guide/) — the dev server and the build
5. [Lucide](https://lucide.dev/) — the icons

## Development

```bash
yarn dev
```

Vite gives a fast dev server with hot reload.

NOTE: If you get a `CSRFTokenError` on your local machine, add `"ignore_csrf": 1`
to `site_config.json`.

### Proxy

The `frappeui` plugin in [vite.config.ts](./vite.config.ts) sets `frappeProxy:
true`. The dev server then sends requests for paths such as `/app`, `/files`,
and `/api` to the site in your bench. The backend API continues to work while
you develop the frontend.

### Build

```bash
yarn build
```

The build writes to `press/public/dashboard`, and the page to
`press/www/dashboard.html`. Frappe serves both.

## Testing

Unit tests use [Vitest](https://vitest.dev/) with [MSW](https://mswjs.io/) for
the API mocks. CI runs them too.

```bash
yarn test
```

End-to-end tests use Playwright and live in `tests-e2e/`. Read
[guide-to-ui-testing.md](../guide-to-ui-testing.md) for the setup.

## Learning more

Start with [main.js](./src/main.js). This file starts the Vue application and
registers the router, the plugins, the controllers, and the global components.
Each part has its own file, which you can find through the imports.

The documentation is not complete. You have to read some `js` and `vue` files.
If you find something to add here, open a PR.
