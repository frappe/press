<template>
	<div>
		<div
			class="mx-auto max-w-2xl rounded-lg border-0 px-2 py-8 sm:border sm:p-8 space-y-8 mt-10"
		>
			<div class="prose prose-sm max-w-none">
				<h1 class="text-2xl font-semibold">Servers</h1>
				<p class="text-p-base">
					With Servers on Frappe Cloud, you now get dedicated compute resources
					for your sites. Servers come in pairs (Application + Database). You
					can run as many sites and bench groups as you want. All other features
					like Private Bench Groups, SSH Access, Database Access work as is with
					servers.
				</p>
			</div>
			<div class="space-y-3">
				<h2 class="text-sm font-semibold tracking-wide text-gray-700">
					Features
				</h2>
				<ul class="space-y-2">
					<li v-for="f in features" :key="f" class="flex items-center gap-2">
						<GreenCheckIcon class="h-4 w-4 shrink-0" />
						<span class="text-sm text-gray-700">{{ f }}</span>
					</li>
				</ul>
				<div>
					<Link
						href="https://docs.frappe.io/cloud/servers/servers-introduction"
						target="_blank"
						class="inline-flex items-center text-sm font-medium text-indigo-600 hover:text-indigo-700"
						>Read more →</Link
					>
				</div>
				<div v-if="!onboardingComplete" class="pt-2">
					<p class="text-sm text-gray-700">
						Finish onboarding to start using Servers.
					</p>
					<Button
						:route="{ name: 'Welcome' }"
						label="Continue Onboarding"
						class="mt-3"
					/>
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import Link from '@/components/Link.vue';

export default {
	name: 'EnableServers',
	components: { Link },
	data() {
		return {
			features: [
				'Unlimited sites & benches (no extra cost)',
				'Isolated benches as separate environments',
				'Frappe Product Warranty for any 5 opted-in sites',
				'One-click vertical scaling to higher plans',
				'Alerts for resource consumption',
				'Features to install, upgrade, backup, monitor & develop apps',
			],
		};
	},
	computed: {
		serversEnabled() {
			return Boolean(this.$team?.doc?.servers_enabled);
		},
		onboardingComplete() {
			return Boolean(this.$team.doc.onboarding?.complete);
		},
	},
	mounted() {
		if (this.onboardingComplete && this.$team.doc.servers_enabled) {
			this.$router.push({ name: 'Server List' });
		}
	},
};
</script>
