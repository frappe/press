<template>
	<Card
		title="Marketplace Subscriptions"
		subtitle="Your marketplace app subscriptions."
		v-if="
			!$resources.marketplaceSubscriptions.loading &&
			marketplaceSubscriptions.length > 0
		"
	>
		<Button v-if="$resources.marketplaceSubscriptions.loading" :loading="true"
			>Loading</Button
		>

		<div v-else-if="$resources.marketplaceSubscriptions.data">
			<div v-if="marketplaceSubscriptions.length === 0">
				<p class="my-3 text-center text-base text-gray-600">
					You don't have any marketplace subscriptions
				</p>
			</div>
			<div v-else class="divide-y">
				<div
					class="grid grid-cols-3 items-center gap-x-8 py-4 text-base text-gray-600 md:grid-cols-5"
				>
					<span>App</span>
					<span class="hidden md:inline">Plan</span>
					<span>Status</span>
					<span class="hidden md:inline">Price</span>
					<span></span>
				</div>

				<div
					v-for="subscription in marketplaceSubscriptions"
					:key="subscription.name"
					class="grid grid-cols-3 items-center gap-x-8 py-4 text-base text-gray-900 md:grid-cols-5"
				>
					<p class="max-w-md truncate text-base font-medium text-gray-700">
						{{ subscription.app_title }}
					</p>
					<p class="hidden text-gray-700 md:inline">
						{{ subscription.plan }}
					</p>
					<span>
						<Badge :label="subscription.status" />
					</span>

					<span class="hidden md:inline" v-if="subscription.is_free">Free</span>
					<span class="hidden md:inline" v-else>
						{{ $planTitle(subscription.plan_info) }}</span
					>

					<span class="shrink-0 text-right">
						<Button @click="changeAppPlan(subscription)">Change Plan</Button>
					</span>
				</div>
			</div>
		</div>

		<ErrorMessage :message="$resources.marketplaceSubscriptions.error" />

		<Dialog v-model="showAppPlanChangeDialog" width="half" :dismissable="true">
			<ChangeAppPlanSelector
				@change="
					plan => {
						newAppPlan = plan.name;
						newAppPlanIsFree = plan.is_free;
					}
				"
				v-if="appToChangePlan"
				:app="appToChangePlan.name"
				:currentPlan="appToChangePlan.plan"
				:frappeVersion="site.frappe_version"
			/>

			<template #actions>
				<Button
					appearance="primary"
					:loading="$resources.changePlan.loading"
					@click="handlePlanChange"
					>Change Plan</Button
				>
			</template>
		</Dialog>
		<Dialog
			v-model="showCheckoutDialog"
			title="Checkout Details"
			:dismissable="true"
		>
			<MarketplacePrepaidCredits
				v-if="newAppPlan"
				:subscription="currentSubscription"
				:app="appToChangePlan.name"
				:site="site.name"
				:plan="newAppPlan"
			/>
		</Dialog>
	</Card>
</template>

<script>
import ChangeAppPlanSelector from '@/components/ChangeAppPlanSelector.vue';
import MarketplacePrepaidCredits from '../marketplace/MarketplacePrepaidCredits.vue';

export default {
	components: { ChangeAppPlanSelector, MarketplacePrepaidCredits },
	props: ['site'],

	data() {
		return {
			showAppPlanChangeDialog: false,
			showCheckoutDialog: false,
			appToChangePlan: null,
			newAppPlan: '',
			newAppPlanIsFree: null,
			currentAppPlan: '',
			currentSubscription: ''
		};
	},

	resources: {
		marketplaceSubscriptions() {
			return {
				method: 'press.api.marketplace.get_marketplace_subscriptions_for_site',
				params: {
					site: this.site?.name
				},
				auto: true
			};
		},

		changePlan() {
			return {
				method: 'press.api.marketplace.change_app_plan',
				onSuccess() {
					this.showAppPlanChangeDialog = false;
					this.$resources.marketplaceSubscriptions.fetch();
				}
			};
		}
	},

	methods: {
		changeAppPlan(subscription) {
			this.currentSubscription = subscription.name;
			this.currentAppPlan = subscription.marketplace_app_plan;
			this.newAppPlan = this.currentAppPlan;

			this.appToChangePlan = {
				name: subscription.app,
				title: subscription.app_title,
				image: subscription.app_image,
				plan: subscription.marketplace_app_plan,
				subscription: subscription.name,
				billing_type: subscription.billing_type
			};
			this.showAppPlanChangeDialog = true;
		},

		handlePlanChange() {
			if (
				this.appToChangePlan.billing_type == 'prepaid' &&
				!this.newAppPlanIsFree
			) {
				if (this.$account.hasBillingInfo) {
					this.showAppPlanChangeDialog = false;
					this.showCheckoutDialog = true;
				} else {
					window.location = '/dashboard/billing';
				}
			} else {
				this.switchToNewPlan();
			}
		},

		switchToNewPlan() {
			if (this.currentAppPlan !== this.newAppPlan) {
				this.$resources.changePlan.submit({
					subscription: this.appToChangePlan.subscription,
					new_plan: this.newAppPlan
				});
			} else {
				this.showAppPlanChangeDialog = false;
			}
		}
	},

	computed: {
		marketplaceSubscriptions() {
			if (
				this.$resources.marketplaceSubscriptions.data &&
				!this.$resources.marketplaceSubscriptions.loading
			) {
				return this.$resources.marketplaceSubscriptions.data;
			}

			return [];
		}
	}
};
</script>
