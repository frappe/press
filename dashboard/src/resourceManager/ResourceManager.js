import call from '../call';

export default class ResourceManager {
	constructor(vm, resourceDefs) {
		this._vm = vm;
		this._watchers = [];
		let resources = {};
		for (let key in resourceDefs) {
			let resourceDef = resourceDefs[key];
			if (typeof resourceDef === 'function') {
				this._watchers.push([
					() => resourceDef.call(vm),
					(n, o) => this.updateResource(key, n, o),
					{
						immediate: true,
						deep: true,
						sync: true
					}
				]);
			} else {
				let resource = new Resource(resourceDef);
				resources[key] = resource;

				if (resource.auto) {
					resource.reload();
				}
			}
		}
		this.resources = resources;
	}

	init() {
		this._watchers = this._watchers.map(w => this._vm.$watch(...w));
	}

	destroy() {
		const vm = this._vm;

		// this.cancelAll();
		// Object.values(this.resources).forEach(r => {
		// 	r.stopInterval();
		// });
		delete vm._rm;
	}

	updateResource(key, newValue, oldValue) {
		let resource;
		if (key in this.resources) {
			resource = this.resources[key];
		} else {
			resource = new Resource(newValue);
			this._vm.$set(this.resources, key, resource);
		}

		let oldData = resource.data;

		// cancel existing fetches
		if (oldValue && resource) {
			resource.cancel();
		}

		resource.update(newValue);
		// keep data if it is needed between refreshes
		if (resource.keepData) {
			resource.data = oldData;
		}

		if (resource.auto) {
			resource.reload();
		}
	}
}

class Resource {
	constructor(options = {}, initialValue) {
		if (typeof options == 'string') {
			options = { method: options, auto: true };
		}
		if (!options.method) {
			throw new Error(
				'[Resource Manager]: method is required to define a resource'
			);
		}

		this.method = options.method;
		this.update(options, initialValue);
	}

	update(options, initialValue) {
		if (typeof options == 'string') {
			options = { method: options, auto: true };
		}
		if (this.method && options.method && options.method !== this.method) {
			throw new Error(
				'[Resource Manager]: method cannot change for the same resource'
			);
		}
		// params
		this.params = options.params || null;
		this.auto = options.auto || false;
		this.keepData = options.keepData || false;
		this.condition = options.condition || (() => true);

		// events
		this.listeners = Object.create(null);
		let listenerKeys = Object.keys(options).filter(key => key.startsWith('on'));
		if (listenerKeys.length > 0) {
			for (const key of listenerKeys) {
				this.on(key, options[key]);
			}
		}

		// response
		this.data = initialValue || null;
		this.error = null;
		this.loading = false;
		this.lastLoaded = null;
	}

	async fetch() {
		if (!this.condition()) return;

		this.loading = true;
		try {
			this.data = await call(this.method, this.params);
			this.emit('Success');
		} catch (error) {
			this.error = error.messages.join('\n');
			this.emit('Error');
		}
		this.lastLoaded = new Date();
		this.loading = false;
	}

	reload() {
		return this.fetch();
	}

	cancel() {}

	on(event, handler) {
		this.listeners[event] = (this.listeners[event] || []).concat(handler);
		return this;
	}

	emit(event) {
		let key = 'on' + event;
		(this.listeners[key] || []).forEach(handler => {
			handler(this, key);
		});
	}
}
