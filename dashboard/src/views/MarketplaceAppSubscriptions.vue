<script setup>
import useResource from '@/composables/resource';

const props = defineProps({
	app: Object
});

const activeSubscriptions = useResource({
	method: 'press.api.marketplace.get_subscriptions_list',
	params: {
		marketplace_app: props.app?.name
	},
	auto: true
});
</script>

<template>
	<Card title="Active Subscriptions">
		<div v-if="activeSubscriptions.data">
			<div v-if="activeSubscriptions.data.length === 0">
				<p class="my-3 text-center text-base text-gray-600">
					Your app has no active subscribers.
				</p>
			</div>
			<div v-else class="divide-y">
				<div
					class="grid grid-cols-3 items-center gap-x-8 py-4 text-base text-gray-600 md:grid-cols-5"
				>
					<span class="col-span-2 md:col-span-1">Site</span>
					<span>Plan</span>
					<span class="hidden md:inline">Price</span>
					<span class="hidden md:inline">Active For</span>
					<span class="hidden md:inline">Contact</span>
				</div>

				<div
					v-for="subscription in activeSubscriptions.data"
					:key="subscription.site"
					class="grid grid-cols-3 items-center gap-x-8 py-4 text-base text-gray-900 md:grid-cols-5"
				>
					<p
						class="col-span-2 max-w-md truncate text-base font-medium text-gray-800 md:col-span-1"
					>
						{{ subscription.site }}
					</p>

					<p class="text-gray-700">
						{{ subscription.app_plan }}
					</p>

					<p class="hidden md:inline">{{ $planTitle(subscription) }} /mo</p>

					<p class="hidden text-gray-700 md:inline">
						{{ subscription.active_days }}
						{{ subscription.active_days == 1 ? 'day' : 'days' }}
					</p>

					<a
						class="hidden underline md:inline"
						:href="`mailto:${subscription.user_contact}`"
					>
						{{ subscription.user_contact }}
					</a>
				</div>
			</div>
		</div>

		<div v-else-if="activeSubscriptions.loading">
			<Button :loading="true">Loading</Button>
		</div>

		<ErrorMessage :error="activeSubscriptions.error" />
	</Card>
</template>
