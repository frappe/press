<template>
	<Card
		title="Apps"
		subtitle="Apps available on your bench"
		:loading="apps.loading"
	>
		<template #actions>
			<Button
				@click="
					installableApps.fetch();
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
				<div class="flex ml-auto space-x-2">
					<Badge v-if="!app.deployed" color="yellow">Not Deployed</Badge>
					<Dropdown :items="dropdownItems(app)" right>
						<template v-slot="{ toggleDropdown }">
							<Button icon="more-horizontal" @click="toggleDropdown()" />
						</template>
					</Dropdown>
				</div>
			</div>
		</div>
		<Dialog title="Add apps to your bench" v-model="showAddAppDialog">
			<div class="divide-y">
				<ListItem
					v-for="app in installableApps.data"
					:key="app.name"
					:title="app.title"
					:subtitle="
						`${app.source.repository_owner}/${app.source.repository}:${app.source.branch}`
					"
				>
					<template #actions>
						<Button
							:loading="addApp.loading && addApp.currentParams.app == app.name"
							@click="
								addApp.submit({
									name: bench.name,
									source: app.source.name,
									app: app.name
								})
							"
						>
							Add App
						</Button>
					</template>
				</ListItem>
			</div>
			<p class="mt-4 text-base" @click="showAddAppDialog = false">
				Don't find your app here?
				<Link :to="`/benches/${bench.name}/apps/new`">
					Add from GitHub
				</Link>
			</p>
		</Dialog>
	</Card>
</template>
<script>
export default {
	name: 'BenchOverviewApps',
	props: ['bench'],
	data() {
		return {
			showAddAppDialog: false
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
