<template>
	<div class="space-y-3">
		<button
			class="block w-full cursor-pointer rounded-md border px-4 py-3 text-left shadow ring-inset focus:outline-none focus:ring-2"
			:class="
				isAppSelected(app)
					? 'bg-blue-50 ring-2 ring-blue-500'
					: 'cursor-pointer hover:border-blue-300'
			"
			v-for="app in apps"
			:key="app.name"
			@click="toggleApp(app.name)"
		>
			<div class="ml-1 flex items-center justify-between text-left text-base">
				<div>
					<div class="font-semibold">
						{{ app.title }}
					</div>
					<div class="text-gray-700">
						{{ app.source.repository_owner }}/{{ app.source.repository }}
					</div>
				</div>
				<Dropdown :items="dropdownItems(app)" right>
					<template v-slot="{ toggleDropdown }">
						<Button
							type="white"
							@click.stop="toggleDropdown()"
							icon-right="chevron-down"
						>
							<span>{{ app.source.branch }}</span>
						</Button>
					</template>
				</Dropdown>
			</div>
		</button>
	</div>
</template>
<script>
export default {
	name: 'AppSourceSelector',
	props: ['apps', 'modelValue', 'multiple'],
	methods: {
		toggleApp(appName) {
			let mapApp = app => ({ app: app.name, source: app.source });

			if (!this.multiple) {
				let selectedApp = this.apps.find(app => app.name === appName);
				this.$emit('update:modelValue', mapApp(selectedApp));
				return;
			}

			// multiple
			let selectedAppsMap = Object.assign({}, this.selectedAppsMap);
			if (selectedAppsMap[appName]) {
				// exists already, remove
				selectedAppsMap[appName] = false;
			} else {
				// add
				selectedAppsMap[appName] = true;
			}
			let selectedApps = this.apps
				.filter(app => selectedAppsMap[app.name])
				.map(mapApp);

			this.$emit('update:modelValue', selectedApps);
		},
		isAppSelected(app) {
			if (this.multiple) {
				return this.selectedAppsMap[app.name];
			}
			return this.modelValue && this.modelValue.app === app.name;
		},
		dropdownItems(app) {
			return app.sources.map(source => ({
				label: `${source.repository_owner}/${source.repository}:${source.branch}`,
				action: () => this.selectSource(app, source)
			}));
		},
		selectSource(app, source) {
			app.source = source;
			if (this.multiple) {
				let selectedApps = this.modelValue.map(_app => {
					if (app.name === _app.app) {
						return {
							app: app.name,
							source
						};
					}
					return _app;
				});
				this.$emit('update:modelValue', selectedApps);
			} else {
				this.$emit('update:modelValue', {
					app: app.name,
					source
				});
			}
		}
	},
	computed: {
		selectedAppsMap() {
			if (!this.multiple) return {};

			let out = {};
			let selectedAppNames = this.modelValue.map(app => app.app);
			for (let app of this.apps) {
				out[app.name] = selectedAppNames.includes(app.name);
			}
			return out;
		}
	}
};
</script>
