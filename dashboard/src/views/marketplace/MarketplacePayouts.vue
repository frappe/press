<script setup>
import useResource from '@/composables/resource';

const payouts = useResource({
	method: 'press.api.marketplace.get_payouts_list',
	auto: true
});
</script>

<template>
	<Card title="Payouts" subtitle="Look what you have earned">
		<Button v-if="payouts.loading" :loading="true">Loading</Button>

		<div v-else-if="payouts.data && payouts.data.length > 0">
			<div class="divide-y">
				<div
					class="grid grid-cols-3 items-center gap-x-8 py-4 text-base text-gray-600 md:grid-cols-5"
				>
					<span>Due Date</span>
					<span class="hidden md:inline">Payment Mode</span>
					<span class="hidden md:inline">Status</span>
					<span>Net INR</span>
					<span>Net USD</span>
				</div>

				<div
					v-for="payout in payouts.data"
					:key="payout.name"
					class="grid grid-cols-3 items-center gap-x-8 py-4 text-base text-gray-900 md:grid-cols-5"
				>
					<div v-if="payout.due_date">
						{{
							$date(payout.due_date).toLocaleString({
								month: 'long',
								day: 'numeric',
								year: 'numeric'
							})
						}}
					</div>
					<div v-else>Not Set</div>

					<div class="hidden md:inline">
						{{ payout.mode_of_payment }}
					</div>

					<div class="hidden md:inline">
						<Badge :status="payout.status" />
					</div>

					<div>₹{{ round(payout.net_total_inr, 2) }}</div>

					<div>${{ round(payout.net_total_usd, 2) }}</div>
				</div>
			</div>
		</div>

		<div v-if="payouts.data && payouts.data.length == 0">
			<p class="my-3 text-center text-base text-gray-600">
				You have no payouts yet.
			</p>
		</div>
		<ErrorMessage :error="payouts.error" />
	</Card>
</template>
