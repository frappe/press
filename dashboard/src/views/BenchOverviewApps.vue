<template>
	<Card
		title="Apps"
		subtitle="Apps available on your bench"
		:loading="apps.loading"
	>
		<template #actions>
			<Button :route="{ name: 'NewApp', params: { benchName: bench.name } }">
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
				<Dropdown class="ml-auto" :items="dropdownItems(app)" right>
					<template v-slot="{ toggleDropdown }">
						<Button icon="more-horizontal" @click="toggleDropdown()" />
					</template>
				</Dropdown>
			</div>
		</div>
	</Card>
</template>
<script>
export default {
	name: 'BenchOverviewApps',
	props: ['bench'],
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
