<template>
	<div>
		<div>
			<PageHeader title="Sites" subtitle="Your Frappe instances">
				<template v-if="this.$account.team.enabled" v-slot:actions>
					<Button
						appearance="primary"
						iconLeft="plus"
						class="ml-2 hidden sm:inline-flex"
						route="/sites/new"
					>
						New
					</Button>
				</template>
			</PageHeader>

			<div class="mb-2" v-if="!$account.team.enabled">
				<Alert title="Your account is disabled">
					Enable your account to start creating sites

					<template #actions>
						<Button appearance="primary" route="/settings">
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
						<Button
							@click="showPrepaidCreditsDialog = true"
							appearance="primary"
						>
							Add Credits
						</Button>
					</template>
				</Alert>

				<Alert v-else title="Your last invoice payment has failed.">
					Pay now for uninterrupted services.
					<template v-if="latestUnpaidInvoiceStripeUrl" #actions>
						<Button
							icon-left="external-link"
							appearance="primary"
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

			<div>
				<SectionHeader heading="Recently Created" />

				<div class="mt-3">
					<LoadingText v-if="$resources.recentSites.loading" />
					<SiteList v-else :sites="recentlyCreatedSites" />
				</div>
			</div>

			<div class="mt-6">
				<SectionHeader heading="All Sites">
					<template v-slot:actions>
						<SiteAndBenchSearch />
					</template>
				</SectionHeader>

				<div class="mt-3">
					<LoadingText v-if="$resources.allSites.loading" />
					<SiteList v-else :sites="sites" />
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import SiteList from './SiteList.vue';
import { defineAsyncComponent } from 'vue';
import SiteAndBenchSearch from '@/components/SiteAndBenchSearch.vue';
import PageHeader from '@/components/global/PageHeader.vue';

export default {
	name: 'Sites',
	props: ['bench'],
	components: {
		SiteList,
		SiteAndBenchSearch,
		PrepaidCreditsDialog: defineAsyncComponent(() =>
			import('@/components/PrepaidCreditsDialog.vue')
		),
		PageHeader
	},
	data() {
		return {
			showPrepaidCreditsDialog: false
		};
	},
	resources: {
		allSites: {
			method: 'press.api.site.all',
			auto: true
		},
		latestUnpaidInvoice: {
			method: 'press.api.billing.get_latest_unpaid_invoice',
			auto: true
		},
		recentSites: {
			method: 'press.api.site.recently_created',
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
		}
	},
	computed: {
		sites() {
			if (!this.$resources.allSites.data) {
				return [];
			}

			return this.$resources.allSites.data;
		},

		recentlyCreatedSites() {
			if (!this.$resources.recentSites.data) {
				return [];
			}

			return this.$resources.recentSites.data;
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
