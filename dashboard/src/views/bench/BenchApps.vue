<template>
	<Card
		title="Apps"
		subtitle="Apps available on your bench"
		:loading="$resources.apps.loading"
	>
		<template #actions>
			<Button
				@click="
					!$resources.installableApps.data
						? $resources.installableApps.fetch()
						: null;
					showAddAppDialog = true;
				"
			>
				Add App
			</Button>
		</template>
		<div class="max-h-96 divide-y">
			<ListItem
				v-for="app in $resources.apps.data"
				:key="app.name"
				:title="app.title"
				:subtitle="`${app.repository_owner}/${app.repository}:${app.branch}`"
			>
				<template #actions>
					<div class="ml-auto flex items-center space-x-2">
						<span
							class="flex flex-row items-center"
							v-if="app.last_github_poll_failed"
						>
							<Tooltip
								class="mr-2 flex cursor-pointer items-center rounded-full bg-gray-100 p-1"
								text="What's this?"
								placement="top"
							>
								<a
									href="https://frappecloud.com/docs/faq/custom_apps#why-does-it-show-attention-required-next-to-my-custom-app"
									target="_blank"
								>
									<FeatherIcon
										class="h-[18px] w-[18px] text-gray-800"
										name="help-circle"
									/>
								</a>
							</Tooltip>

							<Badge color="red"> Attention Required </Badge>
						</span>
						<Badge
							v-if="!app.last_github_poll_failed && !app.deployed"
							color="yellow"
							>Not Deployed</Badge
						>
						<Badge
							v-if="
								!app.last_github_poll_failed &&
								app.update_available &&
								app.deployed
							"
							color="blue"
						>
							Update Available
						</Badge>
						<Dropdown :items="dropdownItems(app)" right>
							<template v-slot="{ toggleDropdown }">
								<Button icon="more-horizontal" @click="toggleDropdown()" />
							</template>
						</Dropdown>
					</div>
				</template>
			</ListItem>
		</div>

		<ErrorMessage :error="$resources.fetchLatestAppUpdate.error" />

		<Dialog
			:options="{ title: 'Add apps to your bench' }"
			v-model="showAddAppDialog"
		>
			<template v-slot:body-content>
				<LoadingText class="py-2" v-if="$resources.installableApps.loading" />
				<AppSourceSelector
					v-else
					class="pt-1"
					:apps="$resources.installableApps.data"
					v-model="selectedApp"
					:multiple="false"
				/>
				<p class="mt-4 text-base" @click="showAddAppDialog = false">
					Don't find your app here?
					<Link :to="`/benches/${benchName}/apps/new`"> Add from GitHub </Link>
				</p>
			</template>
			<template v-slot:actions>
				<Button
					appearance="primary"
					v-if="selectedApp"
					:loading="$resources.addApp.loading"
					@click="
						$resources.addApp.submit({
							name: benchName,
							source: selectedApp.source.name,
							app: selectedApp.app
						})
					"
				>
					Add {{ selectedApp.app }}
				</Button>
			</template>
		</Dialog>

		<ChangeAppBranchDialog
			:bench="benchName"
			v-model:app="appToChangeBranchOf"
		/>
	</Card>
</template>
<script>
import AppSourceSelector from '@/components/AppSourceSelector.vue';
import ChangeAppBranchDialog from '@/components/ChangeAppBranchDialog.vue';

export default {
	name: 'BenchApps',
	components: {
		AppSourceSelector,
		ChangeAppBranchDialog
	},
	props: ['benchName'],
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
					name: this.benchName
				},
				auto: true
			};
		},
		installableApps() {
			return {
				method: 'press.api.bench.installable_apps',
				params: {
					name: this.benchName
				}
			};
		},
		fetchLatestAppUpdate() {
			return {
				method: 'press.api.bench.fetch_latest_app_update',
				onSuccess() {
					window.location.reload();
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
					label: 'Fetch Latest Update',
					action: () => this.fetchLatestUpdate(app)
				},
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
		fetchLatestUpdate(app) {
			this.$resources.fetchLatestAppUpdate.submit({
				name: this.benchName,
				app: app.name
			});
		},
		confirmRemoveApp(app) {
			this.$confirm({
				title: 'Remove App',
				message: `Are you sure you want to remove app ${app.name} from this bench?`,
				actionLabel: 'Remove App',
				actionType: 'danger',
				resource: this.$resources.removeApp,
				action: closeDialog => {
					this.$resources.removeApp.submit({
						name: this.benchName,
						app: app.name
					});
					closeDialog();
				}
			});
		}
	}
};
</script>
