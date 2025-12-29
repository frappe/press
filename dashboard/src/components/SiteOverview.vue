<template>
	<div
		v-if="$site?.doc"
		class="grid grid-cols-1 items-start gap-5 lg:grid-cols-2"
	>
		<CustomAlerts
			:disable-last-child-bottom-margin="true"
			container-class="col-span-1 lg:col-span-2"
			ctx_type="Site"
			:ctx_name="$site?.doc?.name"
		/>

		<AlertBanner
			v-if="$site?.doc?.creation_failed"
			class="col-span-1 lg:col-span-2"
			type="error"
			:title="`Site creation failed. You can restore the site from a backup or drop this site to create a new one. The site will be automatically dropped after ${$site?.doc?.creation_failure_retention_days} days if not restored.`"
		>
		</AlertBanner>

		<AlertBanner
			v-if="$site?.doc?.status === 'Suspended' && $site?.doc?.suspension_reason"
			class="col-span-1 lg:col-span-2"
			type="error"
			:title="`Suspension Reason : ${$site?.doc?.suspension_reason || 'Not Specified'}`"
		>
			<Button
				class="ml-auto min-w-[7rem]"
				variant="outline"
				link="https://docs.frappe.io/cloud/faq/site#my-site-is-suspended-what-do-i-do"
			>
				More Info
			</Button>
		</AlertBanner>

		<AlertBanner
			v-if="$site?.doc?.status === 'Active' && $site?.doc?.site_usage_exceeded"
			class="col-span-1 lg:col-span-2"
			type="warning"
			title="Database or Disk usage limits exceeded. Upgrade plan or reduce usage to avoid suspension."
		>
			<Button
				class="ml-auto min-w-[7rem]"
				variant="outline"
				link="https://docs.frappe.io/cloud/faq/site#my-site-is-suspended-what-do-i-do"
			>
				More Info
			</Button>
		</AlertBanner>

		<AlertBanner
			v-if="!isSetupWizardComplete"
			class="col-span-1 lg:col-span-2"
			title="Please login and complete the setup wizard on your site. Analytics will be
			collected only after setup is complete."
		>
			<Button
				class="ml-auto"
				variant="outline"
				@click="loginAsTeam"
				:loading="$site.loginAsAdmin.loading"
			>
				Login
			</Button>
		</AlertBanner>

		<AlertBanner
			v-if="$site.doc.current_plan?.is_trial_plan"
			class="col-span-1 lg:col-span-2"
			title="Upgrade to a paid plan to continue using your site after the trial period."
		>
			<Button class="ml-auto" variant="outline" @click="showPlanChangeDialog">
				Upgrade
			</Button>
		</AlertBanner>

		<AlertBanner
			v-if="$site.doc.is_monitoring_disabled && $site.doc.status !== 'Archived'"
			class="col-span-1 lg:col-span-2"
			title="Site monitoring is disabled, which means we won’t be able to notify you of any downtime. Please re-enable monitoring at your earliest convenience."
			:id="$site.name"
			type="warning"
		>
		</AlertBanner>
		<DismissableBanner
			v-else-if="$site.doc.eol_versions.includes($site.doc.version)"
			class="col-span-1 lg:col-span-2"
			title="Your site is on an End of Life version. Upgrade to the latest version to get support, latest features and security updates."
			:id="`${$site.name}-eol`"
		>
			<Button
				class="ml-auto min-w-[7rem]"
				variant="outline"
				link="https://docs.frappe.io/cloud/sites/version-upgrade"
			>
				Upgrade Now
			</Button>
		</DismissableBanner>
		<DismissableBanner
			v-else-if="
				$site.doc.current_plan &&
				!$site.doc.current_plan?.private_benches &&
				$site.doc.group_public &&
				!$site.doc.current_plan?.is_trial_plan &&
				$site.doc.status !== 'Archived'
			"
			class="col-span-1 lg:col-span-2"
			title="Your site is currently on a shared bench group. Upgrade plan to enjoy <a href='https://frappecloud.com/shared-hosting#benches' class='underline' target='_blank'>more benefits</a>."
			:id="$site.name"
			type="gray"
		>
			<Button class="ml-auto" variant="outline" @click="showPlanChangeDialog">
				Upgrade Plan
			</Button>
		</DismissableBanner>
		<div class="col-span-1 rounded-md border lg:col-span-2">
			<div class="grid grid-cols-2 lg:grid-cols-4">
				<div class="border-b border-r p-5 lg:border-b-0">
					<div class="flex h-full items-center justify-between">
						<div>
							<div class="text-base text-gray-700">Current Plan</div>
							<div class="mt-2 flex justify-between">
								<div>
									<div class="leading-4">
										<span class="flex items-center text-base text-gray-900">
											<template v-if="$site.doc.trial_end_date">
												{{ trialDays($site.doc.trial_end_date) }}
											</template>
											<template v-else-if="currentPlan">
												{{ $format.planTitle(currentPlan) }}
												<span v-if="currentPlan.price_inr && $isMobile">
													/mo
												</span>
												<span v-if="currentPlan.price_inr && !$isMobile">
													/month
												</span>
											</template>
											<template v-else> No plan set </template>
											<div
												class="ml-2 text-sm leading-3 text-gray-600"
												v-if="
													currentPlan &&
													currentPlan.support_included &&
													!currentPlan.is_trial_plan
												"
											>
												<Tooltip text="Product support included">
													<lucide-badge-check class="h-4 w-4" />
												</Tooltip>
											</div>
										</span>
									</div>
								</div>
							</div>
						</div>
						<Button @click="showPlanChangeDialog">
							{{ currentPlan?.is_trial_plan ? 'Upgrade' : 'Change' }}
						</Button>
					</div>
				</div>
				<div class="border-b p-5 lg:border-b-0 lg:border-r">
					<div
						class="flex items-center justify-between text-base text-gray-700"
					>
						<span>Compute</span>
						<div class="h-7"></div>
					</div>
					<div class="mt-2">
						<Progress
							size="md"
							:value="
								currentPlan
									? (currentUsage.cpu / currentPlan.cpu_time_per_day) * 100
									: 0
							"
						/>
						<div>
							<div class="mt-2 flex justify-between">
								<div class="text-sm text-gray-600">
									{{ currentUsage.cpu }}
									{{ $format.plural(currentUsage.cpu, 'hour', 'hours') }}
									<template
										v-if="currentPlan && !$site.doc.is_dedicated_server"
									>
										of {{ currentPlan?.cpu_time_per_day }} hours
									</template>
								</div>
							</div>
						</div>
					</div>
				</div>
				<div class="border-r p-5">
					<div
						class="flex items-center justify-between text-base text-gray-700"
					>
						<span>Storage</span>
						<div class="h-7"></div>
					</div>
					<div class="mt-2">
						<Progress
							size="md"
							:value="
								currentPlan
									? (currentUsage.storage / currentPlan.max_storage_usage) * 100
									: 0
							"
						/>
						<div>
							<div class="mt-2 flex justify-between">
								<div class="text-sm text-gray-600">
									{{ formatBytes(currentUsage.storage) }}
									<template
										v-if="currentPlan && !$site.doc.is_dedicated_server"
									>
										of {{ formatBytes(currentPlan.max_storage_usage) }}
									</template>
								</div>
							</div>
						</div>
					</div>
				</div>
				<div class="p-5">
					<div
						class="flex min-h-[1.75rem] items-center justify-between text-base text-gray-700"
					>
						<span>Database</span>
						<Button
							v-if="
								(currentPlan
									? (currentUsage.database / currentPlan.max_database_usage) *
										100
									: 0) >= 80
							"
							variant="ghost"
							link="https://docs.frappe.io/cloud/faq/site#what-is-using-up-all-my-database-size"
							icon="help-circle"
						/>
					</div>
					<div class="mt-2">
						<Progress
							size="md"
							:value="
								currentPlan
									? (currentUsage.database / currentPlan.max_database_usage) *
										100
									: 0
							"
						/>
						<div>
							<div class="mt-2 flex justify-between">
								<div class="text-sm text-gray-600">
									{{ formatBytes(currentUsage.database) }}
									<template
										v-if="currentPlan && !$site.doc.is_dedicated_server"
									>
										of
										{{ formatBytes(currentPlan.max_database_usage) }}
									</template>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="rounded-md border">
			<div class="h-12 border-b px-5 py-4">
				<h2 class="text-lg font-medium text-gray-900">Site Information</h2>
			</div>
			<div>
				<div
					v-for="d in siteInformation"
					:key="d.label"
					class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
				>
					<div class="w-1/3 text-base text-gray-600">{{ d.label }}</div>
					<div
						class="flex w-2/3 items-center space-x-2 text-base text-gray-900"
					>
						<div v-if="d.prefix">
							<component :is="d.prefix" />
						</div>
						<span>
							{{ d.value }}
						</span>
						<div v-if="d.suffix">
							<component :is="d.suffix" />
						</div>
					</div>
				</div>
			</div>
		</div>

		<SiteDailyUsage :site="site" />

		<!-- Tags -->
		<div class="col-span-1 flex items-center space-x-2 lg:col-span-2">
			<Badge
				v-for="tag in $site.doc.tags"
				:key="tag.tag"
				:label="tag.tag_name"
				size="lg"
				class="group"
			>
				<template #suffix>
					<button
						@click="removeTag(tag)"
						class="ml-1 hidden transition group-hover:block"
					>
						<lucide-x class="mt-0.5 h-3 w-3" />
					</button>
				</template>
			</Badge>
			<Badge
				variant="outline"
				size="lg"
				label="Add Tag"
				class="cursor-pointer"
				@click="showAddTagDialog"
			>
				<template #suffix>
					<lucide-plus class="h-3 w-3" />
				</template>
			</Badge>
		</div>
	</div>
</template>
<script>
import { getCachedDocumentResource, Progress, Tooltip } from 'frappe-ui';
import { h, defineAsyncComponent } from 'vue';
import { toast } from 'vue-sonner';
import InfoIcon from '~icons/lucide/info';
import DismissableBanner from './DismissableBanner.vue';
import { getToastErrorMessage } from '../utils/toast';
import { renderDialog } from '../utils/components';
import SiteDailyUsage from './SiteDailyUsage.vue';
import AlertBanner from './AlertBanner.vue';
import { trialDays } from '../utils/site';
import CustomAlerts from './CustomAlerts.vue';

export default {
	name: 'SiteOverview',
	props: ['site'],
	components: {
		SiteDailyUsage,
		Progress,
		AlertBanner,
		DismissableBanner,
		CustomAlerts,
	},
	data() {
		return {
			isSetupWizardComplete: true,
		};
	},
	mounted() {
		if (this.$site?.doc?.status === 'Active') {
			this.$site.isSetupWizardComplete.submit().then((res) => {
				this.isSetupWizardComplete = res;
			});
		}
	},
	methods: {
		showPlanChangeDialog() {
			let SitePlansDialog = defineAsyncComponent(
				() => import('../components/ManageSitePlansDialog.vue'),
			);
			renderDialog(h(SitePlansDialog, { site: this.site }));
		},
		showEnableMonitoringDialog() {
			let SiteEnableMonitoringDialog = defineAsyncComponent(
				() => import('./site/SiteEnableMonitoringDialog.vue'),
			);
			renderDialog(h(SiteEnableMonitoringDialog, { site: this.site }));
		},
		formatBytes(v) {
			return this.$format.bytes(v, 2, 2);
		},
		loginAsAdmin() {
			this.$site.loginAsAdmin
				.submit({ reason: '' })
				.then((url) => window.open(url, '_blank'));
		},
		loginAsTeam() {
			if (this.$site.doc?.additional_system_user_created) {
				this.$site.loginAsTeam
					.submit({ reason: '' })
					.then((url) => window.open(url, '_blank'));
			} else {
				this.loginAsAdmin();
			}
		},
		removeTag(tag) {
			toast.promise(
				this.$site.removeTag.submit({
					tag: tag.tag_name,
				}),
				{
					loading: 'Removing tag...',
					success: `Tag ${tag.tag_name} removed`,
					error: (e) => getToastErrorMessage(e),
				},
			);
		},
		showAddTagDialog() {
			const TagsDialog = defineAsyncComponent(
				() => import('../dialogs/TagsDialog.vue'),
			);
			renderDialog(h(TagsDialog, { doctype: 'Site', docname: this.site }));
		},
		trialDays,
	},
	computed: {
		siteInformation() {
			return [
				{
					label: 'Owned by',
					value: this.$site.doc?.owner_email,
				},
				{
					label: 'Created by',
					value: this.$site.doc?.signup_by || this.$site.doc?.owner,
				},
				{
					label: 'Created on',
					value: this.$format.date(
						this.$site.doc?.signup_time || this.$site.doc?.creation,
					),
				},
				{
					label: 'Region',
					value: this.$site.doc?.cluster.title,
					prefix: h('img', {
						src: this.$site.doc?.cluster.image,
						alt: this.$site.doc?.cluster.title,
						class: 'h-4 w-4',
					}),
				},
				{
					label: 'Inbound IP',
					value: this.$site.doc?.inbound_ip,
					suffix: h(
						Tooltip,
						{
							text: 'Use this for adding A records for your site',
						},
						() => h(InfoIcon, { class: 'h-4 w-4 text-gray-500' }),
					),
				},
				{
					label: 'Outbound IP',
					value: this.$site.doc?.outbound_ip,
					suffix: h(
						Tooltip,
						{
							text: 'Use this for whitelisting our server on a 3rd party service',
						},
						() => h(InfoIcon, { class: 'h-4 w-4 text-gray-500' }),
					),
				},
			];
		},
		currentPlan() {
			if (!this.$site?.doc?.current_plan || !this.$team?.doc) return null;

			const currency = this.$team.doc.currency;
			return {
				price:
					currency === 'INR'
						? this.$site.doc.current_plan.price_inr
						: this.$site.doc.current_plan.price_usd,
				price_per_day:
					currency === 'INR'
						? this.$site.doc.current_plan.price_per_day_inr
						: this.$site.doc.current_plan.price_per_day_usd,
				currency: currency === 'INR' ? '₹' : '$',
				...this.$site.doc.current_plan,
			};
		},
		currentUsage() {
			return this.$site.doc?.current_usage;
		},
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
	},
};
</script>
