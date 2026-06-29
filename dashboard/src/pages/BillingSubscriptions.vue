<template>
	<div class="p-5">
		<div
			v-if="$resources.subscriptions.loading"
			class="flex items-center justify-center py-20"
		>
			<Spinner class="h-4 w-4 text-ink-gray-6" />
		</div>
		<div v-else class="mx-auto max-w-3xl space-y-4">
			<!-- Sites -->
			<div class="divide-y rounded border border-outline-gray-1 p-5">
				<div class="pb-3 text-lg font-semibold">Sites</div>
				<p v-if="!data.sites.length" class="py-3 text-p-base text-ink-gray-5">
					No active site subscriptions.
				</p>
				<div
					v-for="site in data.sites"
					:key="site.name"
					class="flex items-center justify-between gap-2 py-3 first:pt-0 last:pb-0"
				>
					<span class="text-base text-ink-gray-9">{{ site.name }}</span>
					<Badge v-if="site.plan" theme="gray" :label="site.plan" />
				</div>
			</div>

			<!-- Servers -->
			<div class="divide-y rounded border border-outline-gray-1 p-5">
				<div class="pb-3 text-lg font-semibold">Servers</div>
				<p v-if="!data.servers.length" class="py-3 text-p-base text-ink-gray-5">
					No active server subscriptions.
				</p>
				<div
					v-for="server in data.servers"
					:key="server.name"
					class="flex items-center justify-between gap-2 py-3 first:pt-0 last:pb-0"
				>
					<span class="text-base text-ink-gray-9">{{ server.name }}</span>
					<Badge v-if="server.plan" theme="gray" :label="server.plan" />
				</div>
			</div>

			<!-- Marketplace Apps -->
			<div class="divide-y rounded border border-outline-gray-1 p-5">
				<div class="pb-3 text-lg font-semibold">Marketplace Apps</div>
				<p
					v-if="!data.marketplace_apps.length"
					class="py-3 text-p-base text-ink-gray-5"
				>
					No active marketplace app subscriptions.
				</p>
				<div
					v-for="app in data.marketplace_apps"
					:key="app.name"
					class="py-3 first:pt-0 last:pb-0"
				>
					<div class="flex items-center justify-between gap-2">
						<span class="text-base font-medium text-ink-gray-9">
							{{ app.title }}
						</span>
						<Badge v-if="app.plan" theme="gray" :label="app.plan" />
					</div>
					<div class="mt-1 text-p-base text-ink-gray-6">
						<span v-if="app.sites.length">
							Installed on: {{ app.sites.join(', ') }}
						</span>
						<span v-else>Not installed on any site.</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import { Badge, Spinner } from 'frappe-ui'

export default {
	name: 'BillingSubscriptions',
	components: { Badge, Spinner },
	resources: {
		subscriptions() {
			return {
				url: 'press.api.billing.subscriptions',
				auto: true,
				initialData: { sites: [], servers: [], marketplace_apps: [] },
			}
		},
	},
	computed: {
		data() {
			return (
				this.$resources.subscriptions.data || {
					sites: [],
					servers: [],
					marketplace_apps: [],
				}
			)
		},
	},
}
</script>
