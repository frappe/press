<template>
	<div class="divide-y mt-2 space-y-2">
		<SelectableCard
			class="w-full"
			v-for="app in appsWithUpdates"
			:key="app.app"
			@click.native="toggleApp(app)"
			:title="app.title"
			:selected="selectedApps.includes(app.app)"
		>
			<template #secondary-content>
				<div class="flex items-center space-x-1">
					<a
						v-if="deployFrom(app)"
						class="block cursor-pointer"
						:href="`${app.repository_url}/commit/${app.current_hash}`"
						target="_blank"
					>
						<Badge class="cursor-pointer hover:text-blue-500" color="blue">
							{{ deployFrom(app) }}
						</Badge>
					</a>
					<FeatherIcon v-if="deployFrom(app)" name="arrow-right" class="w-4" />
					<Badge color="green" v-else>First Deploy</Badge>
					<a
						class="block cursor-pointer"
						:href="`${app.repository_url}/commit/${app.next_hash}`"
						target="_blank"
					>
						<Badge class="cursor-pointer hover:text-blue-500" color="blue">
							{{ deployTo(app) }}
						</Badge>
					</a>
				</div>
			</template>
		</SelectableCard>

		<div v-if="removedApps.length">
			<SelectableCard
				v-for="app in removedApps"
				:key="app"
				class="w-full"
				:title="app"
				:selected="true"
			>
				<template #secondary-content>
					<div class="flex items-center">
						<Badge color="red">Will Be Uninstalled</Badge>
					</div>
				</template>
			</SelectableCard>
		</div>
	</div>
</template>
<script>
import SelectableCard from '@/components/SelectableCard.vue';

export default {
	name: 'BenchAppUpdates',
	props: ['apps', 'removedApps'],
	components: {
		SelectableCard
	},
	data() {
		return {
			selectedApps: []
		};
	},
	mounted() {
		// Select all apps by default
		this.selectedApps = this.appsWithUpdates.map(app => app.app);
		this.$emit('update:selectedApps', this.selectedApps);
	},
	methods: {
		deployFrom(app) {
			if (app.will_branch_change) {
				return app.current_branch;
			}

			return app.current_hash
				? app.current_tag || app.current_hash.slice(0, 7)
				: null;
		},
		deployTo(app) {
			if (app.will_branch_change) {
				return app.branch;
			}

			return app.next_tag || app.next_hash.slice(0, 7);
		},
		toggleApp(app) {
			if (!this.selectedApps.includes(app.app)) {
				this.selectedApps.push(app.app);
				this.$emit('update:selectedApps', this.selectedApps);
			} else {
				this.selectedApps = this.selectedApps.filter(a => a !== app.app);
				this.$emit('update:selectedApps', this.selectedApps);
			}
		}
	},
	computed: {
		appsWithUpdates() {
			return this.apps.filter(app => app.update_available);
		}
	},
	watch: {
		selectedApps(apps) {
			// Hardcoded for now, need a better way
			// to manage such dependencies (#TODO)
			// If updating ERPNext, must update Frappe with it
			if (apps.includes('erpnext') && !apps.includes('frappe')) {
				apps.push('frappe');
			}
		}
	}
};
</script>
