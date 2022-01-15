<template>
	<Card
		title="Marketplace Subscriptions"
		subtitle="Your marketplace app subscriptions."
	>
		<Button v-if="$resources.marketplaceSubscriptions.loading" :loading="true">Loading</Button>

		<div v-else-if="$resources.marketplaceSubscriptions.data">
			<div class="divide-y">
				<div
					class="grid items-center grid-cols-3 py-4 text-base text-gray-600 gap-x-8 md:grid-cols-4"
				>
					<span>App</span>
					<span class="hidden md:inline">Plan</span>
					<span>Status</span>
					<span></span>
				</div>

				<div
					v-for="subscription in marketplaceSubscriptions"
					:key="subscription.name"
					class="grid items-center grid-cols-3 py-4 text-base text-gray-900 gap-x-8 md:grid-cols-4"
				>
					<p class="text-base font-medium text-gray-700 truncate max-w-md">
						{{ subscription.app_title }}
					</p>
					<p class="hidden md:inline text-gray-700">
						{{ subscription.plan_title }}
					</p>
					<span>
						<Badge :status="subscription.status"></Badge>
					</span>
					<span class="text-right">
						<Button>Change Plan</Button>
					</span>
				</div>
			</div>
		</div>

		<ErrorMessage :error="$resources.marketplaceSubscriptions.error" />
	</Card>
</template>

<script>
export default {
	props: ['site'],

	resources: {
		marketplaceSubscriptions() {
			return {
				method: 'press.api.marketplace.get_marketplace_subscriptions_for_site',
				params: {
					site: this.site.name
				},
				auto: true
			}
		}
	},
	
	computed: {
		marketplaceSubscriptions() {
			if (
				this.$resources.marketplaceSubscriptions.data 
				&& !this.$resources.marketplaceSubscriptions.loading
			) {
				return this.$resources.marketplaceSubscriptions.data;
			}

			return [];
		}
	}
};
</script>
