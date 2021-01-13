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
						:key="marketplaceApp.name"
						@click.native="toggleApp(marketplaceApp.app)"
						:title="marketplaceApp.title"
						:image="marketplaceApp.image"
						:selected="selectedApps.includes(marketplaceApp.app.name)"
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
						:key="app.name"
						@click.native="toggleApp(app)"
						:selected="selectedApps.includes(app.name)"
						:title="`${app.repo_owner}/${app.repo}`"
					>
						<div slot="secondary-content" class="text-base text-gray-700">
							{{ app.branch }}
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
	computed: {
		privateApps() {
			return this.apps.filter(
				app => app.team === this.$account.team.name && !app.public
			);
		},
		marketplaceApps() {
			return this.apps
				.filter(app => app.public && !app.frappe)
				.map(app => {
					let options = this.options.marketplace_apps[app.scrubbed];
					if (!options) {
						return false;
					}
					options.app = app;
					return options;
				})
				.filter(Boolean);
		},
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
			let onlyFrappe = this.apps.filter(app => app.frappe).map(app => app.name);
			this.$emit('update:selectedApps', onlyFrappe);
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
