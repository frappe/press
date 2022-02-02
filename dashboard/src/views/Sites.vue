<template>
	<div class="pt-8 pb-20">
		<div class="px-4 sm:px-8">
			<h1 class="sr-only">Dashboard</h1>
			<div class="mb-2" v-if="!$account.team.enabled">
				<Alert title="Your account is disabled">
					Enable your account to start creating sites

					<template #actions>
						<Button type="primary" route="/account/profile">
							Enable Account
						</Button>
					</template>
				</Alert>
			</div>
			<div class="mb-2" v-if="showUnpaidInvoiceAlert">
				<Alert
					v-if="latestUnpaidInvoice.payment_mode == 'Prepaid Credits'"
					title="Your last invoice payment has failed."
				>
					Please add
					<strong>
						{{ latestUnpaidInvoice.currency }}
						{{ latestUnpaidInvoice.amount_due }}
					</strong>
					more in credits.
					<template #actions>
						<Button @click="showPrepaidCreditsDialog = true" type="primary">
							Add Credits
						</Button>
					</template>
				</Alert>

				<Alert v-else title="Your last invoice payment has failed.">
					Pay now for uninterrupted services.
					<template v-if="latestUnpaidInvoiceStripeUrl" #actions>
						<Button
							icon-left="external-link"
							type="primary"
							:link="latestUnpaidInvoiceStripeUrl"
						>
							Pay now
						</Button>
					</template>
				</Alert>

				<PrepaidCreditsDialog
					v-if="showPrepaidCreditsDialog"
					v-model:show="showPrepaidCreditsDialog"
					:minimum-amount="latestUnpaidInvoice.amount_due"
					@success="handleAddPrepaidCreditsSuccess"
				/>
			</div>
<<<<<<< HEAD
<<<<<<< HEAD

			<div class="mb-3 flex flex-row justify-between">
				<SiteAndBenchSearch class="w-full sm:w-60 lg:w-96" />

				<Dropdown :items="newDropdownItems" right>
					<template v-slot="{ toggleDropdown }">
						<Button
							type="primary"
							iconLeft="plus"
							class="ml-2 hidden sm:inline-flex"
							@click.stop="toggleDropdown()"
						>
							New
						</Button>
					</template>
				</Dropdown>
			</div>

			<div v-if="$resources.benches.data == null">
				<div class="flex flex-1 items-center py-4 focus:outline-none">
					<h2 class="text-lg font-semibold">Sites</h2>
=======
			<!-- <div v-if="benches == null">
=======
			<div v-if="benches == null">
>>>>>>> def60e86 (fix: Revert changes in Sites.vue view)
				<div class="flex items-center flex-1 py-4 focus:outline-none">
					<h2 class="text-lg font-semibold">
						Sites
					</h2>
>>>>>>> 1ad99d49 (feat: Complete Main design)
				</div>
				<div class="rounded-md bg-gray-50 px-4 py-3">
					<Loading />
				</div>
			</div>
			<div v-else>
				<div
					v-for="(bench, i) in $resources.benches.data"
					:key="bench.name"
					class="flex flex-col sm:flex-row sm:space-x-4"
					:class="{
						'border-b': i < benches.length - 1 && !isSitesShown(bench),
						'mb-4': isSitesShown(bench)
					}"
				>
					<div class="flex-1">
						<div class="flex items-center justify-between">
							<button
								class="flex flex-1 items-center py-4 text-left focus:outline-none"
								@click="multipleBenches ? toggleSitesShown(bench) : null"
							>
								<h2 class="text-lg font-semibold">
									{{ bench.shared ? 'Sites' : bench.title }}
								</h2>
								<FeatherIcon
									v-if="multipleBenches"
									:name="isSitesShown(bench) ? 'chevron-down' : 'chevron-right'"
									class="ml-1 mt-0.5 h-4 w-4"
								/>
							</button>
							<div class="flex items-center space-x-2">
								<p v-if="benches" class="hidden text-sm text-gray-700 sm:block">
									{{ sitesSubtitle(bench) }}
								</p>
								<Badge
									class="hidden text-sm sm:block"
									v-if="!bench.shared && bench.owned_by_team"
								>
									Private
								</Badge>
								<Button
									v-if="bench.owned_by_team"
									:route="`/benches/${bench.name}`"
									icon="tool"
								>
								</Button>

								<Button
									:route="`/sites/new${
										bench.owned_by_team
											? `?bench=${bench.name}&benchTitle=${bench.title}`
											: ''
									}`"
									type="primary"
									icon="plus"
									v-if="showNewSiteButton(bench)"
									class="sm:hidden"
								>
									New Site
								</Button>
							</div>
						</div>
						<SiteList :sites="bench.sites" v-show="isSitesShown(bench)" />
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import SiteList from './SiteList.vue';
import { defineAsyncComponent } from 'vue';
import SiteAndBenchSearch from '@/components/SiteAndBenchSearch.vue';

export default {
	name: 'Sites',
	props: ['bench'],
	components: {
		SiteList,
		SiteAndBenchSearch,
		PrepaidCreditsDialog: defineAsyncComponent(() =>
			import('@/components/PrepaidCreditsDialog.vue')
		)
	},
	data() {
		return {
			sitesShown: {},
			showPrepaidCreditsDialog: false
		};
	},
	resources: {
		benches: {
			method: 'press.api.site.all',
			auto: true,
			onSuccess(data) {
				if (data && data.length) {
					for (let bench of data) {
						if (!(bench.name in this.sitesShown)) {
							this.sitesShown[bench.name] = Boolean(bench.shared);
						}
					}
				}
			}
		},
		latestUnpaidInvoice: {
			method: 'press.api.billing.get_latest_unpaid_invoice',
			auto: true
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
				let sites = this.benches
					.map(bench => bench.sites.map(site => site.name))
					.flat();
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
				!this.$resources.benches.loading &&
				new Date() - this.$resources.benches.lastLoaded > 5000
			) {
				this.$resources.benches.reload();
			}
		},
		sitesSubtitle(bench) {
			let parts = [];

			if (bench.sites.length > 0) {
				parts.push(
					`${bench.sites.length} ${this.$plural(
						bench.sites.length,
						'site',
						'sites'
					)}`
				);
			}

			if (bench.version) {
				parts.push(bench.version);
			}

			return parts.join(' · ');
		},
		isSitesShown(bench) {
			return this.sitesShown[bench.name];
		},
		toggleSitesShown(bench) {
			this.sitesShown[bench.name] = !this.sitesShown[bench.name];
		},
		showNewSiteButton(bench) {
			if (!this.$account.team.enabled) return false;
			if (bench.status != 'Active') return false;
			return (
				(bench.shared || bench.owned_by_team) && this.sitesShown[bench.name]
			);
		},
		handleAddPrepaidCreditsSuccess() {
			this.$resources.latestUnpaidInvoice.reload();
			this.showPrepaidCreditsDialog = false;
		}
	},
	computed: {
		newDropdownItems() {
			return [
				{
					label: 'Site',
					action: () => {
						this.$router.push('/sites/new');
					}
				},
				{
					label: 'Bench',
					action: () => {
						this.$router.push('/benches/new');
					}
				}
			];
		},
		benches() {
			if (this.$resources.benches.data) {
				return this.$resources.benches.data;
			}
			return null;
		},
		multipleBenches() {
			if (this.$resources.benches.data) {
				return this.$resources.benches.data.length > 1;
			}
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
		},
		latestUnpaidInvoiceStripeUrl() {
			if (this.$resources.latestUnpaidInvoice.data) {
				return this.$resources.latestUnpaidInvoice.data.stripe_invoice_url;
			}
		}
	}
};
</script>
