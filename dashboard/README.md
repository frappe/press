# Dashboard

Dashboard is a VueJS application that is the face of Frappe Cloud. This is what the end users (tenants) see and manage their FC stuff in. The tenants does not have access to the desk, so, this is their dashboard for managing sites, apps, updates etc.

Technologies at the heart of dashboard:

1. [VueJS 3](https://vuejs.org/): The JavaScript framework of our choice.

2. [TailwindCSS 3](https://tailwindcss.com/): We love it.

3. [ViteJS](https://vitejs.dev/guide/): Build tooling for dev server and build command.

4. [Feather Icons](https://feathericons.com/): Those Shiny & Crisp Open Source icons.

## Development

We use the vite's development server, gives us super-fast hot reload and more.

### Running the development server

Run:

```bash
yarn run dev
```

> Note: If you are getting `CSRFTokenError` in your local development machine, please add the following key value pair in your site_cofig.json
>
> ```json
> "ignore_csrf": 1
> ```

### Proxy

While running the vite dev server, the requests to paths like `/app`, `/files` and `/api` are redirected to the actual site inside the bench. This makes sure these paths and other backend API keep working properly. You can check the [proxyOptions.js](./proxyOptions.js) files to check how the proxying happens. These options are then loaded and used in the [vite config](./vite.config.js) file.

## Testing

There is a separate setup for testing the frontend.

### The Stack

1. [MSW](https://mswjs.io/)

2. [Vitest](https://vitest.dev/)

### Running the tests

```bash
yarn run test
```

The tests run in CI too.

## Learning More

You can start by taking a look at the [main.js](./src/main.js) file. This is where the VueJS app is initialzed and the below things are attached (registered) to the instance:

1. Vue Router
2. Plugins
3. Controllers
4. Global Components

The logic to register each of the above is in its own separate file, you can take a look at the imports as required. Till we have a more docs, you have to dig into some `js` and `vue` files. If you find something that you can add here, feel free to raise a PR!
