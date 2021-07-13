<template>
	<div class="space-y-3">
		<button
			class="block w-full px-4 py-3 text-left border rounded-md shadow cursor-pointer focus:outline-none focus:ring-2"
			:class="
				isAppSelected(app)
					? 'ring-2 ring-blue-500 bg-blue-50'
					: 'hover:border-blue-300 cursor-pointer'
			"
			v-for="app in apps"
			:key="app.name"
			@click="toggleApp(app.name)"
		>
			<div class="flex items-center justify-between ml-1 text-base text-left">
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
	props: ['apps', 'value', 'multiple'],
	methods: {
		toggleApp(appName) {
			let mapApp = app => ({ app: app.name, source: app.source });

			if (!this.multiple) {
				let selectedApp = this.apps.find(app => app.name === appName);
				this.$emit('update:value', mapApp(selectedApp));
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

			this.$emit('update:value', selectedApps);
		},
		isAppSelected(app) {
			if (this.multiple) {
				return this.selectedAppsMap[app.name];
			}
			return this.value && this.value.app === app.name;
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
				let selectedApps = this.value.map(_app => {
					if (app.name === _app.app) {
						return {
							app: app.name,
							source
						};
					}
					return _app;
				});
				this.$emit('update:value', selectedApps);
			} else {
				this.$emit('update:value', {
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
			let selectedAppNames = this.value.map(app => app.app);
			for (let app of this.apps) {
				out[app.name] = selectedAppNames.includes(app.name);
			}
			return out;
		}
	}
};
</script>
