<template>
	<div class="mt-8 flex w-2/12 flex-col px-4 pr-4">
		<router-link
			v-for="item in items"
			:key="item.label"
			:to="item.route"
			v-slot="{ href, route, navigate, isActive, isExactActive }"
		>
			<a
				:class="[
					(
						item.highlight
							? item.highlight(route)
							: item.route == '/'
							? isExactActive
							: isActive
					)
						? 'bg-blue-50 text-blue-500'
						: 'text-gray-900 hover:bg-gray-50'
				]"
				:href="href"
				@click="navigate"
				class="text-start mx-2 my-1 flex rounded-md px-4 py-2 text-sm font-medium focus:outline-none"
			>
				<svg
					v-if="item.label == 'Apps'"
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="feather feather-arrow-up-circle mr-1.5 h-4 w-4"
				>
					<circle cx="12" cy="12" r="10"></circle>
					<polyline points="16 12 12 8 8 12"></polyline>
					<line x1="12" y1="16" x2="12" y2="8"></line>
				</svg>
				<svg
					v-if="item.label == 'Billing'"
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="feather feather-file-text mr-1.5 h-4 w-4"
				>
					<path
						d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
					></path>
					<polyline points="14 2 14 8 20 8"></polyline>
					<line x1="16" y1="13" x2="8" y2="13"></line>
					<line x1="16" y1="17" x2="8" y2="17"></line>
					<polyline points="10 9 9 9 8 9"></polyline>
				</svg>
				<svg
					v-if="item.label == 'Settings'"
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="feather feather-settings mr-1.5 h-4 w-4"
				>
					<circle cx="12" cy="12" r="3"></circle>
					<path
						d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"
					></path>
				</svg>
				<svg
					v-if="item.label == 'Developer'"
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="feather feather-sliders mr-1.5 h-4 w-4"
				>
					<line x1="4" y1="21" x2="4" y2="14"></line>
					<line x1="4" y1="10" x2="4" y2="3"></line>
					<line x1="12" y1="21" x2="12" y2="12"></line>
					<line x1="12" y1="8" x2="12" y2="3"></line>
					<line x1="20" y1="21" x2="20" y2="16"></line>
					<line x1="20" y1="12" x2="20" y2="3"></line>
					<line x1="1" y1="14" x2="7" y2="14"></line>
					<line x1="9" y1="8" x2="15" y2="8"></line>
					<line x1="17" y1="16" x2="23" y2="16"></line>
				</svg>
				{{ item.label }}
			</a>
		</router-link>
	</div>
</template>

<script>
export default {
	name: 'Sidebar',
	computed: {
		items() {
			return [
				{
					label: 'Apps',
					route: '/saas/apps',
					highlight: () => {
						return this.$route.fullPath.endsWith('/saas/apps');
					}
				},
				{
					label: 'Billing',
					route: '/saas/billing',
					highlight: () => {
						return this.$route.fullPath.endsWith('/saas/billing');
					}
				},
				{
					label: 'Developer',
					route: '/saas/manage',
					highlight: () => {
						return this.$route.fullPath.endsWith('/saas/manage');
					},
					condition: () => this.$account.team?.is_developer
				},
				{
					label: 'Settings',
					route: '/saas/settings',
					highlight: () => {
						return this.$route.fullPath.endsWith('/saas/setting');
					}
				}
			].filter(d => (d.condition ? d.condition() : true));
		}
	}
};
</script>
