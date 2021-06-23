<template>
	<Card
		title="Apps"
		subtitle="Apps available on your bench"
		:loading="apps.loading"
	>
		<template #actions>
			<Button
				@click="
					!installableApps.data ? installableApps.fetch() : null;
					showAddAppDialog = true;
				"
			>
				Add App
			</Button>
		</template>
		<div class="divide-y">
			<div
				class="flex items-center py-3"
				v-for="app in apps.data"
				:key="app.name"
			>
				<div class="w-1/3 text-base font-medium">
					{{ app.title }}
				</div>
				<div class="text-base text-gray-700">
					{{ app.repository_owner }}:{{ app.branch }}
				</div>
				<div class="flex items-center ml-auto space-x-2">
					<Badge v-if="!app.deployed" color="yellow">Not Deployed</Badge>
					<Badge v-if="app.update_available && app.deployed" color="blue">
						Update Available
					</Badge>
					<Dropdown :items="dropdownItems(app)" right>
						<template v-slot="{ toggleDropdown }">
							<Button icon="more-horizontal" @click="toggleDropdown()" />
						</template>
					</Dropdown>
				</div>
			</div>
		</div>
		<Dialog title="Add apps to your bench" v-model="showAddAppDialog">
			<Loading class="py-2" v-if="installableApps.loading" />
			<AppSourceSelector
				v-else
				class="pt-1"
				:apps="installableApps.data"
				:value.sync="selectedApp"
				:multiple="false"
			/>
			<template #actions>
				<Button
					type="primary"
					v-if="selectedApp"
					:loading="addApp.loading"
					@click="
						addApp.submit({
							name: bench.name,
							source: selectedApp.source.name,
							app: selectedApp.app
						})
					"
				>
					Add {{ selectedApp.app }}
				</Button>
			</template>
			<p class="mt-4 text-base" @click="showAddAppDialog = false">
				Don't find your app here?
				<Link :to="`/benches/${bench.name}/apps/new`">
					Add from GitHub
				</Link>
			</p>
		</Dialog>

		<ChangeAppBranchDialog :bench="bench.name" :app="appToChangeBranchOf" />
	</Card>
</template>
<script>
import AppSourceSelector from '@/components/AppSourceSelector.vue';
import ChangeAppBranchDialog from '@/components/ChangeAppBranchDialog.vue';
export default {
	name: 'BenchOverviewApps',
	components: {
		AppSourceSelector,
		ChangeAppBranchDialog
	},
	props: ['bench'],
	data() {
		return {
			selectedApp: null,
			showAddAppDialog: false,
			appToChangeBranchOf: null
		};
	},
	resources: {
		apps() {
			return {
				method: 'press.api.bench.apps',
				params: {
					name: this.bench.name
				},
				auto: true
			};
		},
		installableApps() {
			return {
				method: 'press.api.bench.installable_apps',
				params: {
					name: this.bench.name
				}
			};
		},
		addApp() {
			return {
				method: 'press.api.bench.add_app',
				onSuccess() {
					window.location.reload();
				}
			};
		},
		removeApp() {
			return {
				method: 'press.api.bench.remove_app'
			};
		}
	},
	methods: {
		dropdownItems(app) {
			return [
				{
					label: 'Remove App',
					action: () => this.confirmRemoveApp(app),
					condition: () => app.name != 'frappe'
				},
				{
					label: 'Change Branch',
					action: () => {
						this.appToChangeBranchOf = app;
					},
					condition: () => app.name != 'frappe'
				},
				{
					label: 'Visit Repo',
					action: () =>
						window.open(`${app.repository_url}/tree/${app.branch}`, '_blank')
				}
			].filter(Boolean);
		},
		confirmRemoveApp(app) {
			this.$confirm({
				title: 'Remove App',
				message: `Are you sure you want to remove app ${app.name} from this bench?`,
				actionLabel: 'Remove App',
				actionType: 'danger',
				action: closeDialog => {
					closeDialog();
					this.$resources.removeApp.submit({
						name: this.bench.name,
						app: app.name
					});
				}
			});
		}
	}
};
</script>
