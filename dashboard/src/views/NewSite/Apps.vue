<template>
	<div class="space-y-6">
		<div>
			<h2 class="text-lg font-semibold">
				Select Frappe Version
			</h2>
			<p class="text-base text-gray-700">
				Select the Frappe version for your site
			</p>
			<div class="mt-4">
				<Input
					type="select"
					v-model="selectedVersion"
					:options="versionOptions"
				/>
			</div>
		</div>
		<div v-if="groupOptions.length >= 2">
			<h2 class="text-lg font-semibold">
				Select Bench
			</h2>
			<p class="text-base text-gray-700">
				Select Bench for your site
			</p>
			<div class="mt-4">
				<Input
					type="select"
					:value="selectedGroup"
					@change="value => $emit('update:selectedGroup', value)"
					:options="groupOptions"
				/>
			</div>
		</div>
		<div>
			<h2 class="text-lg font-semibold">
				Select apps to install
			</h2>
			<p class="text-base text-gray-700">
				Choose apps to install on your site. You can select apps published on
				marketplace or your private apps.
			</p>
			<div class="mt-4">
				<h3 class="sr-only">Marketplace Apps</h3>
				<div
					class="grid grid-cols-2 gap-4 px-2 py-2 mt-4 -mx-2 overflow-y-auto max-h-56"
				>
					<SelectableCard
						v-for="marketplaceApp in marketplaceApps"
						:key="marketplaceApp.app.app"
						@click.native="toggleApp(marketplaceApp.app)"
						:title="marketplaceApp.title"
						:image="marketplaceApp.image"
						:selected="selectedApps.includes(marketplaceApp.app.app)"
					>
						<a
							slot="secondary-content"
							class="inline-block text-sm leading-snug text-blue-600"
							:href="'/' + marketplaceApp.route"
							target="_blank"
							@click.stop
						>
							Details
						</a>
					</SelectableCard>
					<div class="h-1 py-4" v-if="marketplaceApps.length > 4"></div>
				</div>
			</div>
			<div class="mt-4" v-if="privateApps.length > 0">
				<h3 class="text-sm font-medium">
					Your Private Apps
				</h3>
				<div
					class="grid grid-cols-2 gap-4 px-2 py-2 -mx-2 overflow-y-auto mt- max-h-56"
				>
					<SelectableCard
						v-for="app in privateApps"
						:key="app.app"
						@click.native="toggleApp(app)"
						:selected="selectedApps.includes(app.app)"
						:title="app.app_title"
					>
						<div slot="secondary-content" class="text-base text-gray-700">
							{{ app.repository_owner }}:{{ app.branch }}
						</div>
					</SelectableCard>
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import SelectableCard from '@/components/SelectableCard.vue';
export default {
	components: {
		SelectableCard
	},
	name: 'Apps',
	props: ['options', 'selectedApps', 'selectedGroup'],
	data: function() {
		return {
			selectedVersion: null
		};
	},
	computed: {
		privateApps() {
			return this.apps.filter(app => !app.public);
		},
		marketplaceApps() {
			return this.apps
				.filter(app => app.public)
				.map(app => {
					let options = this.options.marketplace_apps[app.app];
					if (!options) {
						return false;
					}
					options.app = app;
					return options;
				})
				.filter(Boolean);
		},
		apps() {
			if (!this.options || !this.selectedVersion || !this.selectedGroup)
				return [];

			let selectedVersion = this.options.versions.find(
				v => v.name == this.selectedVersion
			);
			let group = selectedVersion.groups.find(
				g => g.name == this.selectedGroup
			);
			return group.apps;
		},
		groupOptions() {
			if (!this.options || !this.selectedVersion) return [];
			let selectedVersion = this.options.versions.find(
				version => version.name == this.selectedVersion
			);
			return selectedVersion.groups.map(group => group.name);
		},
		versionOptions() {
			return this.options.versions.map(group => group.name);
		}
	},
	watch: {
		selectedVersion(value) {
			let selectedVersion = this.options.versions.find(v => v.name == value);
			this.$emit('update:selectedGroup', selectedVersion.groups[0].name);
		},
		selectedGroup() {
			this.$emit('update:selectedApps', ['frappe']);
		}
	},
	async mounted() {
		this.selectedVersion = this.options.versions[0].name;
	},
	methods: {
		toggleApp(app) {
			if (app.frappe) return;
			if (!this.selectedApps.includes(app.app)) {
				this.$emit('update:selectedApps', this.selectedApps.concat(app.app));
			} else {
				this.$emit(
					'update:selectedApps',
					this.selectedApps.filter(a => a !== app.app)
				);
			}
		}
	}
};
</script>
