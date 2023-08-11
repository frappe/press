<template>
	<div class="space-y-8">
		<Table
			:columns="[
				{ label: 'Site Name', name: 'name', width: 2 },
				{ label: 'Status', name: 'status' },
				{ label: 'Region', name: 'region' },
				{ label: 'Tags', name: 'tags' },
				{ label: 'Plan', name: 'plan' },
				{ label: '', name: 'actions', width: 0.5 }
			]"
			:rows="sites"
			v-slot="{ rows, columns }"
		>
			<TableHeader />
			<div class="flex items-center justify-center">
				<LoadingText class="mt-8" v-if="$resources.versions.loading" />
				<div v-else-if="rows.length === 0" class="mt-8">
					<div class="text-base text-gray-700">No Items</div>
				</div>
			</div>
			<div v-for="(group, i) in groups" :key="group.name">
				<div
					class="flex w-full items-center justify-between border-b bg-gray-50 px-3 py-2 text-base"
				>
					<span class="font-semibold text-gray-900">
						{{ group.name }}
					</span>
					<Dropdown
						:options="[
							{
								label: 'Show app versions',
								onClick: () => {
									showAppsDialog = true;
									selectedGroupIndex = i;
								}
							}
						]"
					>
						<template v-slot="{ open }">
							<Button variant="ghost">
								<template #icon>
									<FeatherIcon name="more-horizontal" class="h-4 w-4" />
								</template>
							</Button>
						</template>
					</Dropdown>
				</div>

				<TableRow
					v-for="row in sitesByGroup[group.name]"
					:key="row.name"
					:row="row"
				>
					<TableCell v-for="column in columns">
						<Badge
							class="ring-1 ring-white"
							v-if="column.name === 'status'"
							:label="siteBadge(row)"
						/>
						<div
							v-else-if="column.name === 'tags' && row.tags"
							class="-space-x-5"
						>
							<Badge
								class="ring-1 ring-white"
								v-for="(tag, i) in row.tags.slice(0, 2)"
								:theme="$getColorBasedOnString(i)"
								:label="tag"
							/>
							<Badge
								class="ring-1 ring-white"
								v-if="row.tags.length > 2"
								:label="`+${row.tags.length - 2}`"
							/>
						</div>
						<span v-else-if="column.name === 'plan'">
							{{ row.plan ? `${$planTitle(row.plan)}/mo` : '' }}
						</span>
						<div v-else-if="column.name === 'region'">
							<img
								v-if="row.server_region_info?.image"
								class="h-4"
								:src="row.server_region_info.image"
								:alt="`Flag of ${row.server_region_info.title}`"
								:title="row.server_region_info.image"
							/>
							<span class="text-base text-gray-700" v-else>
								{{ row.server_region_info?.title }}
							</span>
						</div>
						<div class="w-full text-right" v-else-if="column.name == 'actions'">
							<Dropdown @click.prevent :options="dropdownItems(row)">
								<template v-slot="{ open }">
									<Button
										:variant="open ? 'subtle' : 'ghost'"
										icon="more-horizontal"
									/>
								</template>
							</Dropdown>
						</div>
						<span v-else>{{ row[column.name] || '' }}</span>
					</TableCell>
				</TableRow>
			</div>
		</Table>
	</div>

	<Dialog :options="{ title: 'Apps' }" v-model="showAppsDialog">
		<template #body-content>
			<ListItem
				v-for="app in groups[selectedGroupIndex].apps"
				:key="app.app"
				:title="app.app"
				:subtitle="`${app.repository_owner}/${app.repository}:${app.branch}`"
			>
				<template #actions>
					<CommitTag
						:tag="app.tag || app.hash.substr(0, 7)"
						class="ml-2"
						:link="`${app.repository_url}/commit/${app.hash}`"
					/>
				</template>
			</ListItem>
		</template>
	</Dialog>

	<Dialog
		:options="{
			title: 'Login As Administrator',
			actions: [
				{
					label: 'Proceed',
					variant: 'solid',
					onClick: proceedWithLoginAsAdmin
				}
			]
		}"
		v-model="showReasonForAdminLoginDialog"
	>
		<template #body-content>
			<FormControl
				label="Reason for logging in as Administrator"
				type="textarea"
				v-model="reasonForAdminLogin"
				required
			/>
			<ErrorMessage class="mt-3" :message="errorMessage" />
		</template>
	</Dialog>
</template>
<script>
import { loginAsAdmin } from '@/controllers/loginAsAdmin';
import Table from '@/components/Table/Table.vue';
import TableHeader from '@/components/Table/TableHeader.vue';
import TableRow from '@/components/Table/TableRow.vue';
import TableCell from '@/components/Table/TableCell.vue';
import CommitTag from '@/components/utils/CommitTag.vue';
import { FeatherIcon } from 'frappe-ui';

export default {
	name: 'BenchSites',
	props: ['bench', 'benchName'],
	components: {
		Table,
		TableHeader,
		TableRow,
		TableCell,
		CommitTag,
		FeatherIcon
	},
	data() {
		return {
			reasonForAdminLogin: '',
			errorMessage: null,
			selectedGroupIndex: 0,
			showAppsDialog: false,
			showReasonForAdminLoginDialog: false,
			siteForLogin: null
		};
	},
	resources: {
		benchesWithSites() {
			return {
				method: 'press.api.bench.benches_with_sites',
				params: {
					name: this.bench?.name
				},
				auto: true
			};
		},
		versions() {
			return {
				method: 'press.api.bench.versions',
				params: {
					name: this.benchName
				},
				auto: true
			};
		},
		loginAsAdmin() {
			return loginAsAdmin('placeholderSite'); // So that RM does not yell at first load
		}
	},
	methods: {
		dropdownItems(site) {
			return [
				{
					label: 'Visit Site',
					onClick: () => {
						window.open(`https://${site.name}`, '_blank');
					}
				},
				{
					label: 'Login As Admin',
					onClick: () => {
						if (this.$account.team.name === site.team) {
							return this.$resources.loginAsAdmin.submit({
								name: site.name
							});
						}

						this.siteForLogin = site.name;
						this.showReasonForAdminLoginDialog = true;
					}
				}
			];
		},
		proceedWithLoginAsAdmin() {
			this.errorMessage = '';

			if (!this.reasonForAdminLogin.trim()) {
				this.errorMessage = 'Reason is required';
				return;
			}

			this.$resources.loginAsAdmin.submit({
				name: this.siteForLogin,
				reason: this.reasonForAdminLogin
			});

			this.showReasonForAdminLoginDialog = false;
		},
		siteBadge(site) {
			let status = site.status;
			if (site.update_available && site.status == 'Active') {
				status = 'Update Available';
			}

			let usage = Math.max(
				site.current_cpu_usage,
				site.current_database_usage,
				site.current_disk_usage
			);
			if (usage && usage >= 80 && status == 'Active') {
				status = 'Attention Required';
			}
			if (site.trial_end_date) {
				status = 'Trial';
			}
			return status;
		}
	},
	computed: {
		sites() {
			if (!this.$resources.benchesWithSites.data) return [];
			return this.$resources.benchesWithSites.data.flatMap(bench => {
				return bench.sites.map(site => {
					site.bench = bench.bench;
					site.apps = bench.apps;
					return site;
				});
			});
		},
		sitesByGroup() {
			let sitesByGroup = {};

			for (let site of this.sites) {
				let bench = site.bench;
				if (!sitesByGroup[bench]) {
					sitesByGroup[bench] = [];
				}
				site.route = {
					name: 'SiteOverview',
					params: {
						siteName: site.name
					}
				};
				sitesByGroup[bench].push(site);
			}

			return sitesByGroup;
		},
		groups() {
			let seen = [];
			let groups = [];
			for (let site of this.sites) {
				if (!seen.includes(site.bench)) {
					seen.push(site.bench);
					groups.push({
						name: site.bench,
						apps: site.apps
					});
				}
			}
			return groups;
		}
	}
};
</script>
