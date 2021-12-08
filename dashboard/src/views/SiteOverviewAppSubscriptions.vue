<template>
	<Card
		title="Marketplace Subscriptions"
		subtitle="Your marketplace app subscriptions."
	>
		<div>
			<div class="divide-y">
				<div
					class="grid items-center grid-cols-3 py-4 text-base text-gray-600 gap-x-8 md:grid-cols-5"
				>
					<span>App</span>
					<span class="hidden md:inline">Plan</span>
					<span>Status</span>
					<span class="hidden md:inline">Expiry</span>
					<span></span>
				</div>

				<div
					v-for="subscription in marketplaceSubscriptions"
					:key="subscription.name"
					class="grid items-center grid-cols-3 py-4 text-base text-gray-900 gap-x-8 md:grid-cols-5"
				>
					<p class="text-base font-medium text-gray-700 truncate max-w-md">
						{{ subscription.app }}
					</p>
					<p class="hidden md:inline text-gray-700">
						{{ subscription.plan }}
					</p>
					<span>
						<Badge :status="subscription.status"></Badge>
					</span>
					<span class="hidden md:inline text-gray-600">
						{{ subscription.expiry }}
					</span>
					<span class="text-right">
						<Button>{{ subscription.button_text }}</Button>
					</span>
				</div>
			</div>
		</div>
	</Card>
</template>

<script>
export default {
	props: ['site'],
	data() {
		return {
			marketplaceSubscriptions: [
				{
					app: 'Frappe QMail',
					plan: '$25 / mo (1000 emails/day)',
					name: 'jhdfgjdf',
					status: 'Active',
					expiry: '10th January, 2022',
					button_text: 'Change Plan'
				},
				{
					app: 'Healthcare',
					plan: '$30 / mo (Premium Support)',
					name: 'jhdfgjdf',
					status: 'Expired',
					expiry: '7th November, 2021',
					button_text: 'Renew Plan'
				}
			]
		};
	}
};
</script>
