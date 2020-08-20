<template>
	<div>
		<label class="text-lg font-semibold">
			Select apps to install
		</label>
		<p class="text-base text-gray-700">
			Choose apps to install on your site. You can also choose a specific
			version of the app.
		</p>
		<div class="mt-4">
			<Input
				type="select"
				:value="selectedGroup"
				@change="value => $emit('update:selectedGroup', value)"
				:options="groupOptions"
			/>
		</div>
		<div class="mt-6">
			<div class="flex py-2 pl-1 -my-2 -ml-1 overflow-x-auto">
				<button
					class="relative flex items-center justify-center py-4 pl-4 pr-8 mr-4 border rounded-md cursor-pointer focus:outline-none focus:shadow-outline"
					:class="
						selectedApps.includes(app.name)
							? 'bg-blue-50 border-blue-500'
							: 'hover:border-blue-400'
					"
					v-for="app in apps"
					:key="app.name"
					@click="toggleApp(app)"
				>
					<div class="flex items-start">
						<Input
							class="pt-0.5 pointer-events-none"
							tabindex="-1"
							type="checkbox"
							:value="selectedApps.includes(app.name)"
						/>
						<div class="ml-3 text-base text-left">
							<div class="font-semibold">
								{{ app.repo_owner }}/{{ app.repo }}
							</div>
							<div class="text-gray-700">
								{{ app.branch }}
							</div>
						</div>
					</div>
				</button>
			</div>
		</div>
	</div>
</template>
<script>
export default {
	name: 'Apps',
	props: ['options', 'selectedApps', 'selectedGroup'],
	computed: {
		apps() {
			if (!this.options) return [];

			let group = this.options.groups.find(g => g.name == this.selectedGroup);
			return group.apps;
		},
		groupOptions() {
			return this.options.groups.map(option => option.name);
		}
	},
	watch: {
		selectedGroup: {
			handler: 'resetAppSelection',
			immediate: true
		}
	},
	methods: {
		resetAppSelection() {
			this.$emit('update:selectedApps', []);
			let frappeApp = this.apps.find(app => app.frappe);
			if (frappeApp) {
				this.$emit('update:selectedApps', [frappeApp.name]);
			}
		},
		toggleApp(app) {
			if (app.frappe) return;
			if (!this.selectedApps.includes(app.name)) {
				this.$emit('update:selectedApps', this.selectedApps.concat(app.name));
			} else {
				this.$emit(
					'update:selectedApps',
					this.selectedApps.filter(a => a !== app.name)
				);
			}
		}
	}
};
</script>
