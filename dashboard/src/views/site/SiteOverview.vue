<script setup>
import { computed, ref } from 'vue';
import { utils } from '@/utils';
import { createResource } from 'frappe-ui';
import SiteOverviewPlan from './SiteOverviewPlan.vue';
import SiteOverviewInfo from './SiteOverviewInfo.vue';
import SiteOverviewDomains from './SiteOverviewDomains.vue';
import SiteOverviewCPUUsage from './SiteOverviewCPUUsage.vue';
import AlertSiteUpdate from '@/components/AlertSiteUpdate.vue';
import AlertSiteActivation from '@/components/AlertSiteActivation.vue';
import SiteActivity from './SiteActivity.vue';

const props = defineProps({ site: Object });
const showPromotionalDialog = ref(false);
const clickedPromotion = ref(null);

const overview = createResource({
	url: 'press.api.site.overview',
	params: { name: props.site?.name },
	auto: true
});

const closeToLimits = computed(() => {
	if (!(props.site && overview.data)) return false;
	let usage = overview.data.plan.usage_in_percent;
	return [usage.cpu, usage.database, usage.disk].some(x => 100 >= x && x > 80);
});

const limitExceeded = computed(() => {
	if (!(props.site && overview.data)) return false;
	let usage = overview.data.plan.usage_in_percent;
	return [usage.cpu, usage.database, usage.disk].some(x => x > 100);
});

const isInTrial = computed(() => {
	return props.site?.trial_end_date;
});

const trialEndsText = computed(() => {
	if (!props.site?.trial_end_date) {
		return 0;
	}
	return utils.methods.trialEndsInDaysText(props.site.trial_end_date);
});

const marketplacePromotionalBanners =  createResource({
	url: 'press.api.marketplace.get_promotional_banners',
	auto: true
});
</script>

<template>
	<div class="space-y-5" v-if="site">
		<AlertSiteActivation :site="site" />
		<AlertSiteUpdate :site="site" />

		<div
			v-if="
				marketplacePromotionalBanners.data &&
				marketplacePromotionalBanners.data.length > 0
			"
		>
			<Alert
				v-for="banner in marketplacePromotionalBanners.data"
				:title="banner.alert_title"
				:key="banner.name"
			>
				{{ banner.alert_message }}

				<template #actions>
					<Button
						class="whitespace-nowrap"
						variant="solid"
						@click="
							() => {
								showPromotionalDialog = true;
								clickedPromotion = banner;
							}
						"
					>
						Learn More
					</Button>
				</template>
			</Alert>
		</div>
		<Alert title="Trial" v-if="isInTrial && $account.needsCard">
			Your trial ends {{ trialEndsText }} after which your site will get
			suspended. Add your billing information to avoid suspension.

			<template #actions>
				<Button class="whitespace-nowrap" route="/welcome" variant="solid">
					Add Billing Information
				</Button>
			</template>
		</Alert>
		<Alert title="Trial" v-if="isInTrial && $account.hasBillingInfo">
			Your trial ends {{ trialEndsText }} after which your site will get
			suspended. Select a plan from the Plan section below to avoid suspension.
		</Alert>
		<Alert title="Attention Required" v-if="limitExceeded">
			Your site has exceeded the allowed usage for your plan. Upgrade your plan
			now.
		</Alert>
		<Alert title="Attention Required" v-else-if="closeToLimits">
			Your site has exceeded 80% of the allowed usage for your plan. Upgrade
			your plan now.
		</Alert>

		<div
			class="grid grid-cols-1 gap-5 sm:grid-cols-2"
			v-if="site && overview.data"
		>
			<SiteOverviewCPUUsage :site="site" />
			<SiteOverviewPlan
				:site="site"
				:plan="overview.data.plan"
				@plan-change="overview.reload()"
			/>
			<SiteOverviewInfo :site="site" :info="overview.data.info" />
			<SiteOverviewDomains :site="site" />
			<SiteActivity :site="site" />
		</div>

		<Dialog
			v-model="showPromotionalDialog"
			@close="e => (clickedPromotion = null)"
			:options="{
				title: 'Frappe Cloud Marketplace',
				actions: [
					{
						variant: 'solid',
						route: `/install-app/${clickedPromotion?.app}`,
						label: 'Install App'
					}
				]
			}"
		>
			<template #body-content>
				<div v-if="clickedPromotion" class="flex flex-row items-center">
					<Avatar
						class="mr-2"
						size="lg"
						shape="square"
						:imageURL="clickedPromotion.image"
						:label="clickedPromotion.title"
					/>

					<div class="flex flex-col">
						<h4 class="text-xl font-semibold text-gray-900">
							{{ clickedPromotion.title }}
						</h4>
						<p class="text-base text-gray-600">
							{{ clickedPromotion.description }}
						</p>
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>
