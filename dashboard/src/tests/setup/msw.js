import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { config } from '@vue/test-utils';
import resourceManager from '@/resourceManager';
import { components } from '@/components/global/register';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';

import fetch from 'node-fetch';

const restHandlers = [
	rest.post(
		'http://fc.tests/api/method/press.api.site.features',
		(req, res, ctx) => {
			return res(ctx.status(200), ctx.json({ message: apps }));
		}
	)
];

const server = setupServer(...restHandlers);

beforeAll(() => {
	setupGlobalConfig(config); // Plugins, global components etc.

	// Have to mock fetch, since tests run in node environment
	vi.stubGlobal('fetch', (url, options) =>
		fetch('http://fc.tests' + url, options)
	);

	// Starts the msw server
	server.listen({ onUnhandledRequest: 'error' });
});

// Close server after all tests
afterAll(() => server.close());

afterEach(() => server.resetHandlers());

function setupGlobalConfig(config) {
	const globalComponents = {};
	for (let path in components) {
		let component = components[path];
		let name = path.replace('./', '').replace('.vue', '');
		globalComponents[name] = component.default || component;
	}

	config.global.components = globalComponents;
	config.global.plugins = [resourceManager];
}
