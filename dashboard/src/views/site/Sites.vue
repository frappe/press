<template>
	<div>
		<div>
			<header
				class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
			>
				<BreadCrumbs :items="[{ label: 'Sites', route: { name: 'Sites' } }]">
					<template v-if="this.$account.team.enabled" #actions>
						<Button
							variant="solid"
							icon-left="plus"
							class="ml-2"
							label="Create"
							@click="showBillingDialog"
						>
						</Button>
					</template>
				</BreadCrumbs>
			</header>

			<div class="my-5 space-y-2 px-5">
				<div v-if="!$account.team.enabled">
					<Alert title="Your account is disabled">
						Enable your account to start creating sites
						<template #actions>
							<Button variant="solid" route="/settings/profile">
								Enable Account
							</Button>
						</template>
					</Alert>
				</div>
				<AlertBillingInformation />
				<template v-if="showUnpaidInvoiceAlert">
					<Alert
						v-if="latestUnpaidInvoice.payment_mode === 'Prepaid Credits'"
						title="Your last invoice payment has failed."
					>
						Please add
						<strong>
							{{ latestUnpaidInvoice.currency }}
							{{ latestUnpaidInvoice.amount_due }}
						</strong>
						more in credits.
						<template #actions>
							<Button @click="showPrepaidCreditsDialog = true" variant="solid">
								Add Credits
							</Button>
						</template>
					</Alert>

					<Alert v-else title="Your last invoice payment has failed.">
						Pay now for uninterrupted services.
						<template v-if="this.$resources.latestUnpaidInvoice.data" #actions>
							<router-link
								:to="{ path: '/billing', query: { invoiceStatus: 'Unpaid' } }"
							>
								<Button variant="solid"> Go to Billing </Button>
							</router-link>
						</template>
					</Alert>

					<PrepaidCreditsDialog
						v-if="showPrepaidCreditsDialog"
						v-model:show="showPrepaidCreditsDialog"
						:minimum-amount="Math.ceil(latestUnpaidInvoice.amount_due)"
						@success="handleAddPrepaidCreditsSuccess"
					/>
				</template>
			</div>
			<div class="mx-5">
				<div class="pb-20">
					<div class="flex">
						<div class="flex w-full space-x-2 pb-4">
							<FormControl label="Search Sites" v-model="searchTerm">
								<template #prefix>
									<FeatherIcon name="search" class="w-4 text-gray-600" />
								</template>
							</FormControl>
							<FormControl
								label="Status"
								class="mr-8"
								type="select"
								:options="siteStatusFilterOptions()"
								v-model="siteFilter.status"
							/>
							<FormControl
								label="Tag"
								class="mr-8"
								type="select"
								:options="siteTagFilterOptions()"
								v-model="siteFilter.tag"
							/>
						</div>
					</div>
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
							<LoadingText class="mt-8" v-if="$resources.allSites.loading" />
							<div v-else-if="rows.length === 0" class="mt-8">
								<div class="text-base text-gray-700">No sites</div>
							</div>
						</div>

						<div v-for="group in groups" :key="group.group">
							<div
								class="flex w-full items-center border-b bg-gray-50 px-3 py-2 text-base"
							>
								<span class="font-semibold text-gray-900">
									{{ group.title }}
								</span>
								<span v-if="!group.public" class="ml-2 text-gray-600">{{
									group.version
								}}</span>
								<Button
									v-if="!group.public"
									variant="ghost"
									class="ml-auto"
									:route="{ name: 'Bench', params: { benchName: group.group } }"
								>
									View Bench
								</Button>
								<div v-else class="h-7" />
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
										:label="$siteStatus(row)"
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
										{{
											row.plan
												? `${$planTitle(row.plan)}${
														row.plan.price_usd > 0 ? '/mo' : ''
												  }`
												: ''
										}}
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
									<div
										class="w-full text-right"
										v-else-if="column.name == 'actions'"
									>
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
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import { defineAsyncComponent } from 'vue';
import Table from '@/components/Table/Table.vue';
import TableHeader from '@/components/Table/TableHeader.vue';
import TableRow from '@/components/Table/TableRow.vue';
import TableCell from '@/components/Table/TableCell.vue';
import { loginAsAdmin } from '@/controllers/loginAsAdmin';
import PageHeader from '@/components/global/PageHeader.vue';
import AlertBillingInformation from '@/components/AlertBillingInformation.vue';
import Fuse from 'fuse.js/dist/fuse.basic.esm';

export default {
	name: 'Sites',
	pageMeta() {
		return {
			title: 'Sites - Frappe Cloud'
		};
	},
	props: ['bench'],
	components: {
		Table,
		TableHeader,
		TableRow,
		TableCell,
		PageHeader,
		PrepaidCreditsDialog: defineAsyncComponent(() =>
			import('@/components/PrepaidCreditsDialog.vue')
		),
		StripeCard: defineAsyncComponent(() =>
			import('@/components/StripeCard.vue')
		),
		AlertBillingInformation
	},
	data() {
		return {
			showPrepaidCreditsDialog: false,
			showAddCardDialog: false,
			searchTerm: '',
			reasonForAdminLogin: '',
			errorMessage: null,
			showReasonForAdminLoginDialog: false,
			siteForLogin: null,
			siteFilter: {
				status: 'All',
				tag: ''
			}
		};
	},
	resources: {
		allSites() {
			return {
				method: 'press.api.site.all',
				params: { site_filter: this.siteFilter },
				auto: true,
				onSuccess: data => {
					this.fuse = new Fuse(data, {
						keys: ['name', 'tags']
					});
				}
			};
		},
		siteTags: 'press.api.site.site_tags',
		latestUnpaidInvoice: {
			method: 'press.api.billing.get_latest_unpaid_invoice',
			auto: true
		},
		loginAsAdmin() {
			return loginAsAdmin('placeholderSite'); // So that RM does not yell at first load
		}
	},
	mounted() {
		this.$socket.on('agent_job_update', this.onAgentJobUpdate);
		this.$socket.on('list_update', this.onSiteUpdate);
	},
	unmounted() {
		this.$socket.off('agent_job_update', this.onAgentJobUpdate);
		this.$socket.off('list_update', this.onSiteUpdate);
	},
	methods: {
		showBillingDialog() {
			if (!this.$account.hasBillingInfo) {
				this.showAddCardDialog = true;
			} else {
				this.$router.replace('/sites/new');
			}
		},
		onAgentJobUpdate(data) {
			if (!(data.name === 'New Site' || data.name === 'New Site from Backup'))
				return;
			if (data.status === 'Success' && data.user === this.$account.user.name) {
				this.reload();
				this.$notify({
					title: 'Site creation complete!',
					message: 'Login to your site and complete the setup wizard',
					icon: 'check',
					color: 'green'
				});
			}
		},
		onSiteUpdate(event) {
			// Refresh if the event affects any of the sites in the list view
			// TODO: Listen to a more granular event than list_update
			if (event.doctype === 'Site') {
				let sites = this.sites;
				if (
					event.user === this.$account.user.name ||
					sites.includes(event.name)
				) {
					this.reload();
				}
			}
		},
		reload() {
			// refresh if currently not loading and have not reloaded in the last 5 seconds
			if (
				!this.$resources.allSites.loading &&
				new Date() - this.$resources.allSites.lastLoaded > 5000
			) {
				this.$resources.allSites.reload();
			}
		},
		handleAddPrepaidCreditsSuccess() {
			this.$resources.latestUnpaidInvoice.reload();
			this.showPrepaidCreditsDialog = false;
		},
		siteStatusFilterOptions() {
			return [
				{
					label: 'All',
					value: 'All'
				},
				{
					label: 'Active',
					value: 'Active'
				},
				{
					label: 'Broken',
					value: 'Broken'
				},
				{
					label: 'Trial',
					value: 'Trial'
				},
				{
					label: 'Update Available',
					value: 'Update Available'
				}
			];
		},
		siteTagFilterOptions() {
			const defaultOptions = [
				{
					label: '',
					value: ''
				}
			];

			if (!this.$resources.siteTags.data) return defaultOptions;

			return [
				...defaultOptions,
				...this.$resources.siteTags.data.map(tag => ({
					label: tag,
					value: tag
				}))
			];
		},
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
		}
	},
	computed: {
		sites() {
			if (!this.$resources.allSites.data) {
				return [];
			}
			let sites = this.$resources.allSites.data.filter(site =>
				this.$account.hasPermission(site.name, '', true)
			);
			if (this.searchTerm) {
				return this.fuse.search(this.searchTerm).map(result => result.item);
			}
			return sites;
		},
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
				if (site.public) {
					site.title = 'Shared';
					site.group = 'Shared';
				}
				if (!seen.includes(site.group)) {
					seen.push(site.group);
					groups.push({
						title: site.title,
						group: site.group,
						public: site.public,
						version: site.version
					});
				}
			}
			return groups;
		},
		showUnpaidInvoiceAlert() {
			if (!this.latestUnpaidInvoice) {
				return;
			}
			return !(
				this.$account.team.erpnext_partner || this.$account.team.free_account
			);
		},
		latestUnpaidInvoice() {
			if (this.$resources.latestUnpaidInvoice.data) {
				return this.$resources.latestUnpaidInvoice.data;
			}
		}
	}
};
</script>
