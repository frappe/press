<template>
	<div class="p-5">
		<div
			v-if="$resources.subscriptions.loading"
			class="flex items-center justify-center py-20"
		>
			<Spinner class="h-4 w-4 text-ink-gray-6" />
		</div>
		<div v-else class="mx-auto max-w-3xl space-y-5">
			<!-- Sites -->
			<div class="overflow-hidden rounded-lg border border-outline-gray-2">
				<div
					class="flex items-center gap-2 border-b border-outline-gray-2 bg-surface-gray-1 px-4 py-3"
				>
					<lucide-panel-top class="h-4 w-4 text-ink-gray-6" />
					<h3 class="text-base font-medium text-ink-gray-9">Sites</h3>
					<span class="text-p-sm text-ink-gray-5">{{ data.sites.length }}</span>
				</div>
				<div class="divide-y divide-outline-gray-1">
					<p
						v-if="!data.sites.length"
						class="px-4 py-6 text-center text-p-base text-ink-gray-5"
					>
						No active site subscriptions.
					</p>
					<div
						v-for="site in data.sites"
						:key="site.name"
						class="flex items-center justify-between gap-2 px-4 py-3 transition-colors hover:bg-surface-gray-1"
					>
						<div class="flex items-center gap-2.5 truncate">
							<lucide-globe class="h-4 w-4 shrink-0 text-ink-gray-5" />
							<span class="truncate text-base text-ink-gray-8"
								>{{ site.name }}</span
							>
						</div>
						<Badge v-if="site.plan" theme="gray" :label="site.plan" />
					</div>
				</div>
			</div>

			<!-- Servers -->
			<div class="overflow-hidden rounded-lg border border-outline-gray-2">
				<div
					class="flex items-center gap-2 border-b border-outline-gray-2 bg-surface-gray-1 px-4 py-3"
				>
					<lucide-server class="h-4 w-4 text-ink-gray-6" />
					<h3 class="text-base font-medium text-ink-gray-9">Servers</h3>
					<span class="text-p-sm text-ink-gray-5"
						>{{ data.servers.length }}</span
					>
				</div>
				<div class="divide-y divide-outline-gray-1">
					<p
						v-if="!data.servers.length"
						class="px-4 py-6 text-center text-p-base text-ink-gray-5"
					>
						No active server subscriptions.
					</p>
					<div
						v-for="server in data.servers"
						:key="server.name"
						class="flex items-center justify-between gap-2 px-4 py-3 transition-colors hover:bg-surface-gray-1"
					>
						<div class="flex items-center gap-2.5 truncate">
							<lucide-server class="h-4 w-4 shrink-0 text-ink-gray-5" />
							<span class="truncate text-base text-ink-gray-8"
								>{{ server.name }}</span
							>
						</div>
						<Badge v-if="server.plan" theme="gray" :label="server.plan" />
					</div>
				</div>
			</div>

			<!-- Marketplace Apps -->
			<div class="overflow-hidden rounded-lg border border-outline-gray-2">
				<div
					class="flex items-center gap-2 border-b border-outline-gray-2 bg-surface-gray-1 px-4 py-3"
				>
					<lucide-blocks class="h-4 w-4 text-ink-gray-6" />
					<h3 class="text-base font-medium text-ink-gray-9">
						Marketplace Apps
					</h3>
					<span class="text-p-sm text-ink-gray-5"
						>{{ data.marketplace_apps.length }}</span
					>
				</div>
				<div class="divide-y divide-outline-gray-1">
					<p
						v-if="!data.marketplace_apps.length"
						class="px-4 py-6 text-center text-p-base text-ink-gray-5"
					>
						No active marketplace app subscriptions.
					</p>
					<div
						v-for="app in data.marketplace_apps"
						:key="app.name"
						class="px-4 py-3 transition-colors hover:bg-surface-gray-1"
					>
						<div class="flex items-center justify-between gap-2">
							<div class="flex items-center gap-2.5 truncate">
								<lucide-blocks class="h-4 w-4 shrink-0 text-ink-gray-5" />
								<span class="truncate text-base text-ink-gray-8"
									>{{ app.title }}</span
								>
							</div>
							<Badge v-if="app.plan" theme="gray" :label="app.plan" />
						</div>
						<div
							v-if="app.sites.length"
							class="mt-2 flex flex-wrap items-center gap-1.5 pl-[26px]"
						>
							<span class="text-p-sm text-ink-gray-5">Installed on</span>
							<Badge
								v-for="site in app.sites"
								:key="site"
								theme="gray"
								:label="site"
							/>
						</div>
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
