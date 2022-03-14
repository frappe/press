// Authors: Faris Ansari <faris@frappe.io> & Hussain Nagaria <hussain@frappe.io>

import ResourceManager from './ResourceManager';
import { reactive } from 'vue';

let plugin = {
	beforeCreate() {
		const vmOptions = this.$options;
		if (!vmOptions.resources || vmOptions._rm) return;

		let resourceManager;
		if (typeof vmOptions.resources === 'function') {
			vmOptions.resources = vmOptions.resources.call(this);
		}

		if (isPlainObject(vmOptions.resources)) {
			const { $options, ...resourceDefs } = vmOptions.resources;
			resourceManager = new ResourceManager(this, resourceDefs);
		} else {
			throw new Error(
				'[ResourceManager]: resources options should be an object or a function that returns object'
			);
		}

		if (!Object.prototype.hasOwnProperty.call(this, '$resources')) {
			this.$resources = reactive(resourceManager.resources);
		}

		Object.keys(vmOptions.resources).forEach(key => {
			if (
				!(
					hasKey(vmOptions.computed, key) ||
					hasKey(vmOptions.props, key) ||
					hasKey(vmOptions.methods, key)
				)
			) {
				if (!vmOptions.computed) {
					vmOptions.computed = {};
				}

				vmOptions.computed[key] = vmOptions.resources[key];
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
	created() {
		if (!this._rm) return;
		this._rm.init();
	}
};

export default function install(app) {
	app.mixin(plugin);
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
