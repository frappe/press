import ResourceManager from './ResourceManager';

let plugin = {
	beforeCreate() {
		const vmOptions = this.$options;
		if (!vmOptions.resources || vmOptions._rm) return;

		let resourceManager;
		// function style
		if (typeof vmOptions.resources === 'function') {
			vmOptions.resources = vmOptions.resources.call(this);
		}
		if (isPlainObject(vmOptions.resources)) {
			const { $options, ...resourceDefs } = vmOptions.resources;
			resourceManager = new ResourceManager(this, resourceDefs, $options);
		} else {
			throw new Error(
				'[ResourceManager]: resources options should be an object or a function that returns object'
			);
		}

		if (!Object.prototype.hasOwnProperty.call(this, '$resources')) {
			Object.defineProperty(this, '$resources', {
				get: () => resourceManager.resources
			});
		}

		Object.keys(vmOptions.resources).forEach(key => {
			if (
				!(
					hasKey(vmOptions.computed, key) ||
					hasKey(vmOptions.props, key) ||
					hasKey(vmOptions.methods, key)
				)
			) {
				vmOptions.computed = Object.assign(vmOptions.computed || {}, {
					[key]() {
						return this.$resources[key];
					}
				});
			}
		});

		this._rm = resourceManager;
	},

	data() {
		if (!this._rm) return {};
		return {
			$rm: this._rm,
			$r: this._rm.resources,
			$resources: this._rm.resources
		};
	},

	computed: {
		$resourceErrors() {
			if (!this._rm) return '';
			return Object.keys(this.$resources)
				.map(key => this.$resources[key].error)
				.filter(Boolean)
				.join('\n');
		}
	},

	created() {
		if (!this._rm) return;
		this._rm.init();
	},

	beforeDestroy() {
		if (!this._rm) return;
		this._rm.destroy();
	}
};

export default function install(Vue) {
	Vue.mixin(plugin);
}

function isPlainObject(value) {
	return (
		typeof value === 'object' &&
		value &&
		Object.prototype.toString(value) === '[object Object]'
	);
}

function hasKey(object, key) {
	return key in (object || {});
}
