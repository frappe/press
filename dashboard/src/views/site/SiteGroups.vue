<template>
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
		v-slot="{ columns }"
	>
		<TableHeader />

		<div v-for="group in groups" :key="group.group">
			<div
				class="flex w-full items-center border-b bg-gray-50 px-3 py-2 text-base"
			>
				<span class="font-semibold text-gray-900">
					{{ group.title }}
				</span>
				<span class="ml-2 text-gray-600">{{ group.version }}</span>
				<Button
					variant="ghost"
					class="ml-auto"
					:route="{ name: 'Bench', params: { benchName: group.group } }"
				>
					View Bench
				</Button>
			</div>

			<TableRow
				v-for="row in sitesByGroup[group.group]"
				:key="row.name"
				:row="row"
			>
				<TableCell v-for="column in columns">
					<Badge
						class="ring-1 ring-white"
						v-if="column.name === 'status'"
						:label="siteBadge(row)"
					/>
					<div v-else-if="column.name === 'tags'" class="-space-x-5">
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
							v-if="row.server_region_info.image"
							class="h-4"
							:src="row.server_region_info.image"
							:alt="`Flag of ${row.server_region_info.title}`"
							:title="row.server_region_info.image"
						/>
						<span class="text-base text-gray-700" v-else>
							{{ row.server_region_info.title }}
						</span>
					</div>
					<div class="w-full text-right" v-else-if="column.name == 'actions'">
						<Dropdown @click.prevent :options="dropdownItems(row)">
							<template v-slot="{ open }">
								<Button
									:variant="open ? 'subtle' : 'ghost'"
									class="mr-2"
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
import SiteList from './SiteList.vue';
import Table from '@/components/Table/Table.vue';
import TableHeader from '@/components/Table/TableHeader.vue';
import TableRow from '@/components/Table/TableRow.vue';
import TableCell from '@/components/Table/TableCell.vue';

export default {
	name: 'SiteGroups',
	props: {
		sites: {
			default: []
		},
		showBenchInfo: {
			default: true
		}
	},
	components: {
		SiteList,
		Table,
		TableHeader,
		TableRow,
		TableCell
	},
	data() {
		return {
			reasonForAdminLogin: '',
			errorMessage: null,
			showReasonForAdminLoginDialog: false,
			siteForLogin: null
		};
	},
	resources: {
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
					},
					condition: () =>
						site.status === 'Active' || site.status === 'Updating'
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
					},
					condition: () =>
						site.status === 'Active' || site.status === 'Updating'
				},
				{
					label: 'Manage Bench',
					onClick: () => {
						this.$router.push({
							name: 'Bench',
							params: { benchName: site.group }
						});
					},
					condition: () => true
				}
			].filter(item => item.condition());
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
		sitesByGroup() {
			let sitesByGroup = {};

			for (let site of this.sites) {
				let group = site.group;
				if (!sitesByGroup[group]) {
					sitesByGroup[group] = [];
				}
				site.route = {
					name: 'SiteOverview',
					params: {
						siteName: site.name
					}
				};
				sitesByGroup[group].push(site);
			}

			return sitesByGroup;
		},
		groups() {
			let seen = [];
			let groups = [];
			for (let site of this.sites) {
				if (!seen.includes(site.group)) {
					seen.push(site.group);
					groups.push({
						title: site.title,
						group: site.group,
						version: site.version
					});
				}
			}
			return groups;
		}
	}
};
</script>
