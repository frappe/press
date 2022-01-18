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
			</div> -->

			<!-- Temp App Reviews Design -->
			<div class="max-w-4xl">
				<div>
					<div class="mb-9 flex flex-row justify-between">
						<h2 class="text-2xl text-gray-900 font-bold">Customer Reviews</h2>
						<Button>Write a Review</Button>
					</div>

					<div
						class="pl-4 flex flex-row space-x-1 divide-opacity-95 divide-x-2"
					>
						<div class="text-center pr-11">
							<h3 class="text-6xl text-gray-900 font-bold">4.7</h3>
							<p class="text-base text-gray-600">128 ratings</p>
							<div
								class="flex flex-row space-x-1 mt-3 mb-1 bg-gray-100 py-2 px-3 rounded-full"
							>
								<!-- Star Icon -->
								<svg
									v-for="i in [1, 2, 3, 4, 5]"
									:key="i"
									xmlns="http://www.w3.org/2000/svg"
									width="14"
									height="14"
									viewBox="0 0 14 14"
									fill="none"
								>
									<path
										d="M6.56866 0.735724C6.76184 0.406233 7.23816 0.406233 7.43134 0.735725L9.16063 3.68535C9.23112 3.80559 9.34861 3.89095 9.48475 3.92084L12.8244 4.65401C13.1974 4.73591 13.3446 5.18892 13.091 5.47446L10.8201 8.03059C10.7275 8.1348 10.6826 8.27291 10.6963 8.41162L11.031 11.8144C11.0684 12.1945 10.683 12.4745 10.3331 12.3214L7.20032 10.9516C7.07261 10.8958 6.92739 10.8958 6.79968 10.9516L3.66691 12.3214C3.31696 12.4745 2.9316 12.1945 2.96899 11.8144L3.30371 8.41162C3.31736 8.27291 3.27248 8.1348 3.17991 8.03059L0.90903 5.47446C0.655358 5.18892 0.802551 4.73591 1.17561 4.65401L4.51525 3.92084C4.65139 3.89095 4.76888 3.80559 4.83937 3.68535L6.56866 0.735724Z"
										:fill="i > 4 ? '#C0C6CC' : '#ECAC4B'"
									/>
								</svg>
							</div>
							<p class="text-sm text-gray-600">4.7 out of 5</p>
						</div>
						<!-- Star percentages section -->
						<div class="pl-11 space-y-2">
							<div
								class="flex flex-row text-gray-600 text-sm items-center space-x-2"
							>
								<p>5 Star</p>
								<div class="w-28 h-1 bg-gray-200 rounded-full">
									<div class="h-1 bg-gray-600 rounded-full w-2/3"></div>
								</div>
								<p>85%</p>
							</div>
							<div
								class="flex flex-row text-gray-600 text-sm items-center space-x-2"
							>
								<p>4 Star</p>
								<div class="w-28 h-1 bg-gray-200 rounded-full">
									<div class="h-1 bg-gray-600 rounded-full w-2/3"></div>
								</div>
								<p>67%</p>
							</div>
							<div
								class="flex flex-row text-gray-600 text-sm items-center space-x-2"
							>
								<p>3 Star</p>
								<div class="w-28 h-1 bg-gray-200 rounded-full">
									<div class="h-1 bg-gray-600 rounded-full w-1/2"></div>
								</div>
								<p>48%</p>
							</div>
							<div
								class="flex flex-row text-gray-600 text-sm items-center space-x-2"
							>
								<p>2 Star</p>
								<div class="w-28 h-1 bg-gray-200 rounded-full">
									<div class="h-1 bg-gray-600 rounded-full w-7"></div>
								</div>
								<p>32%</p>
							</div>
							<div
								class="flex flex-row text-gray-600 text-sm items-center space-x-2"
							>
								<p>1 Star</p>
								<div class="w-28 h-1 bg-gray-200 rounded-full">
									<div class="h-1 bg-gray-600 rounded-full w-3.5"></div>
								</div>
								<p>20%</p>
							</div>
						</div>
					</div>

					<!-- Written reviews section -->
					<div class="mt-12 divide-y-2 divide-gray-200">
						<!-- Review 1 -->
						<div class="pb-3">
							<div class="mb-2 flex flex-row items-center">
								<h3 class="text-gray-900 font-semibold text-lg">
									Best in market!
								</h3>
								<div>
									<!-- Star Component -->
									<div class="flex flex-row space-x-1 ml-3">
										<!-- Star Icon -->
										<svg
											v-for="i in [1, 2, 3, 4, 5]"
											:key="i"
											xmlns="http://www.w3.org/2000/svg"
											width="14"
											height="14"
											viewBox="0 0 14 14"
											fill="none"
										>
											<path
												d="M6.56866 0.735724C6.76184 0.406233 7.23816 0.406233 7.43134 0.735725L9.16063 3.68535C9.23112 3.80559 9.34861 3.89095 9.48475 3.92084L12.8244 4.65401C13.1974 4.73591 13.3446 5.18892 13.091 5.47446L10.8201 8.03059C10.7275 8.1348 10.6826 8.27291 10.6963 8.41162L11.031 11.8144C11.0684 12.1945 10.683 12.4745 10.3331 12.3214L7.20032 10.9516C7.07261 10.8958 6.92739 10.8958 6.79968 10.9516L3.66691 12.3214C3.31696 12.4745 2.9316 12.1945 2.96899 11.8144L3.30371 8.41162C3.31736 8.27291 3.27248 8.1348 3.17991 8.03059L0.90903 5.47446C0.655358 5.18892 0.802551 4.73591 1.17561 4.65401L4.51525 3.92084C4.65139 3.89095 4.76888 3.80559 4.83937 3.68535L6.56866 0.735724Z"
												:fill="i > 5 ? '#C0C6CC' : '#ECAC4B'"
											/>
										</svg>
									</div>
								</div>
							</div>
							<p class="text-base text-gray-900 mb-2">
								Writing this after a week of purchase. I cannot express the
								awesomeness of this product. Everything just seems to be perfect
								be it the display, the battery, the appearance and most of all
								the performance. Totally in love with this. Go for it without
								having a second thought.
							</p>
							<div class="text-base text-gray-600">
								Tanay Shandilya &bull; 27 days ago
							</div>
						</div>

						<!-- Review 2 -->
						<div class="py-3">
							<div class="mb-2 flex flex-row items-center">
								<h3 class="text-gray-900 font-semibold text-lg">
									Awesome!
								</h3>
								<div>
									<!-- Star Component -->
									<div class="flex flex-row space-x-1 ml-3">
										<!-- Star Icon -->
										<svg
											v-for="i in [1, 2, 3, 4, 5]"
											:key="i"
											xmlns="http://www.w3.org/2000/svg"
											width="14"
											height="14"
											viewBox="0 0 14 14"
											fill="none"
										>
											<path
												d="M6.56866 0.735724C6.76184 0.406233 7.23816 0.406233 7.43134 0.735725L9.16063 3.68535C9.23112 3.80559 9.34861 3.89095 9.48475 3.92084L12.8244 4.65401C13.1974 4.73591 13.3446 5.18892 13.091 5.47446L10.8201 8.03059C10.7275 8.1348 10.6826 8.27291 10.6963 8.41162L11.031 11.8144C11.0684 12.1945 10.683 12.4745 10.3331 12.3214L7.20032 10.9516C7.07261 10.8958 6.92739 10.8958 6.79968 10.9516L3.66691 12.3214C3.31696 12.4745 2.9316 12.1945 2.96899 11.8144L3.30371 8.41162C3.31736 8.27291 3.27248 8.1348 3.17991 8.03059L0.90903 5.47446C0.655358 5.18892 0.802551 4.73591 1.17561 4.65401L4.51525 3.92084C4.65139 3.89095 4.76888 3.80559 4.83937 3.68535L6.56866 0.735724Z"
												:fill="i > 4 ? '#C0C6CC' : '#ECAC4B'"
											/>
										</svg>
									</div>
								</div>
							</div>
							<p class="text-base text-gray-900 mb-2">
								Received it in perfect conditions within the specified time. I
								had also exchanged my old lappy. No problem during the
								exchange.A big thumbs up to flipkart for the packing with extra
								dunnage..
							</p>
							<div class="text-base text-gray-600">
								Faris Ansari &bull; 5 days ago
							</div>
						</div>
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
