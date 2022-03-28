<template>
	<div>
		<!-- App Selector -->
		<div
			class="flex cursor-pointer items-center rounded-lg px-2 py-2"
			v-on:click="() => (isHidden = false)"
		>
			<Avatar size="md" :label="'T'" />
			<p class="ml-4 text-lg">Frappe Teams</p>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
				class="feather feather-chevron-down ml-1.5 h-4 w-4"
			>
				<polyline points="6 9 12 15 18 9"></polyline>
			</svg>
		</div>
		<!-- -->

		<div
			class="top-200 absolute flex flex-col rounded-lg border bg-white px-1 py-1 shadow"
			:class="{ hidden: isHidden }"
		>
			<div
				class="flex cursor-pointer items-center rounded-lg px-2 py-2"
				:class="'hover:bg-gray-100'"
				v-for="sub in subscriptions"
				:key="sub.site"
				@click="switchSaasSite(sub.site)"
			>
				<Avatar size="md" :label="'T'" />
				<div class="ml-4 mr-4">
					<p class="text-base">{{ sub.app_name }}</p>
					<p class="text-sm text-gray-500">{{ sub.site }}</p>
				</div>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="#8B8B8B"
					stroke-width="1.5"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="feather feather-check float-right ml-auto h-4 w-4"
					v-if="selectedSite == sub.site"
				>
					<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
					<polyline points="22 4 12 14.01 9 11.01"></polyline>
				</svg>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'SaasAppSwitcher',
	data() {
		return {
			isHidden: true,
			subscriptions: null,
			selectedSite: localStorage.getItem('current_saas_site')
		};
	},
	methods: {
		switchSaasSite(site) {
			this.$saas.switchToSaas(site);
		},
		toggleAppSwitcher() {
			this.isHidden = !this.isHidden;
		}
	},
	resources: {
		subs: {
			method: 'press.api.saas.get_saas_subscriptions_for_team',
			auto: true,
			onSuccess(r) {
				this.subscriptions = r;
				// set active subscription here
			}
		}
	}
};
</script>
