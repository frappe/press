<template>
	<div class="space-y-5">
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
				>
					<template #subtitle>
						<div class="mt-1 flex items-center space-x-2 text-gray-600">
							<FeatherIcon name="git-branch" class="h-4 w-4" />
							<div class="truncate text-base hover:text-clip">
								{{ app.repository_owner }}/{{ app.repository }}:{{ app.branch }}
							</div>
						</div>
					</template>
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

								<Badge label="Attention Required" theme="red" />
							</span>
							<Badge
								v-if="!app.last_github_poll_failed && !app.deployed"
								label="Not Deployed"
								theme="orange"
							/>
							<Badge
								v-if="
									!app.last_github_poll_failed &&
									app.update_available &&
									app.deployed
								"
								label="Update Available"
								theme="blue"
							/>
							<Dropdown :options="dropdownItems(app)" right>
								<template v-slot="{ open }">
									<Button icon="more-horizontal" />
								</template>
							</Dropdown>
						</div>
					</template>
				</ListItem>
			</div>

			<ErrorMessage :message="$resources.fetchLatestAppUpdate.error" />

			<Dialog
				:options="{ title: 'Add apps to your bench', position: 'top' }"
				v-model="showAddAppDialog"
			>
				<template v-slot:body-content>
					<FormControl
						class="mb-2"
						placeholder="Search for Apps"
						v-on:input="e => updateSearchTerm(e.target.value)"
					/>
					<LoadingText class="py-2" v-if="$resources.installableApps.loading" />
					<AppSourceSelector
						v-else
						class="max-h-96 overflow-auto p-1"
						:class="filteredOptions.length > 5 ? 'pr-2' : ''"
						:apps="filteredOptions"
						v-model="selectedApps"
						:multiple="true"
					/>
					<p class="mt-4 text-base" @click="showAddAppDialog = false">
						Don't find your app here?
						<Link :to="`/benches/${benchName}/apps/new`">
							Add from GitHub
						</Link>
					</p>
				</template>
				<template v-slot:actions>
					<Button
						variant="solid"
						class="w-full"
						v-if="selectedApps.length > 0"
						:loading="$resources.addApps.loading"
						@click="
							$resources.addApps.submit({
								name: benchName,
								apps: selectedApps.map(app => ({
									app: app.app,
									source: app.source.name
								}))
							})
						"
					>
						Add App{{ selectedApps.length > 1 ? 's' : '' }}
					</Button>
				</template>
			</Dialog>

			<ChangeAppBranchDialog
				:bench="benchName"
				v-model:app="appToChangeBranchOf"
			/>
		</Card>
	</div>
</template>
<script>
import AppSourceSelector from '@/components/AppSourceSelector.vue';
import ChangeAppBranchDialog from '@/components/ChangeAppBranchDialog.vue';
import Fuse from 'fuse.js/dist/fuse.basic.esm';
import { notify } from '@/utils/toast';

export default {
	name: 'BenchApps',
	components: {
		AppSourceSelector,
		ChangeAppBranchDialog
	},
	props: ['benchName', 'bench'],
	data() {
		return {
			selectedApps: [],
			showAddAppDialog: false,
			appToChangeBranchOf: null,
			searchTerm: '',
			filteredOptions: []
		};
	},
	resources: {
		apps() {
			return {
				url: 'press.api.bench.apps',
				params: {
					name: this.benchName
				},
				auto: true
			};
		},
		installableApps() {
			return {
				url: 'press.api.bench.installable_apps',
				params: {
					name: this.benchName
				},
				onSuccess(data) {
					this.fuse = new Fuse(data, {
						limit: 20,
						keys: ['title']
					});
					this.filteredOptions = data;
				}
			};
		},
		fetchLatestAppUpdate() {
			return {
				url: 'press.api.bench.fetch_latest_app_update',
				onSuccess() {
					window.location.reload();
				}
			};
		},
		addApps() {
			return {
				url: 'press.api.bench.add_apps',
				onSuccess() {
					window.location.reload();
				}
			};
		},
		removeApp() {
			return {
				url: 'press.api.bench.remove_app',
				onSuccess(app_name) {
					this.$resources.apps.setData(data =>
						data.filter(app => app.name !== app_name)
					);
				},
				onError(e) {
					notify({
						title: 'Error',
						message: e,
						icon: 'x',
						color: 'red'
					});
				}
			};
		}
	},
	methods: {
		updateSearchTerm(value) {
			if (value) {
				this.filteredOptions = this.fuse
					.search(value)
					.map(result => result.item);
			} else {
				this.filteredOptions = this.$resources.installableApps.data;
			}
		},
		dropdownItems(app) {
			return [
				{
					label: 'View in Desk',
					onClick: () =>
						window.open(
							`${window.location.protocol}//${window.location.host}/app/app/${app.name}`,
							'_blank'
						),
					condition: () => this.$account.user.user_type == 'System User'
				},
				{
					label: 'Fetch Latest Update',
					onClick: () => this.fetchLatestUpdate(app)
				},
				{
					label: 'Remove App',
					onClick: () => this.confirmRemoveApp(app),
					condition: () => app.name != 'frappe'
				},
				{
					label: 'Change Branch',
					onClick: () => {
						this.appToChangeBranchOf = app;
					}
				},
				{
					label: 'Visit Repo',
					onClick: () =>
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
				actionColor: 'red',
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
