<template>
	<div class="flex flex-col">
		<router-link
			v-for="item in items"
			:key="item.label"
			:to="item.route"
			v-slot="{ href, route, navigate }"
		>
			<a
				:class="[
					(Boolean(item.highlight) ? item.highlight(route) : item.route == '/')
						? 'bg-blue-50 text-blue-500'
						: 'text-gray-900 hover:bg-gray-50'
				]"
				:href="href"
				@click="navigate"
				class="text-start mb-2 flex rounded-md py-2 pl-2 pr-10 text-sm font-medium focus:outline-none"
			>
				<Component class="mr-1.5" :is="item.icon" />
				{{ item.label }}
			</a>
		</router-link>
	</div>
</template>

<script>
import { FCIcons } from '@/components/icons';

export default {
	name: 'Sidebar',
	computed: {
		items() {
			return [
				{
					label: 'Sites',
					route: '/sites',
					highlight: route => {
						return this.$route.fullPath.indexOf('/sites') >= 0;
					},
					icon: FCIcons.SiteIcon
				},
				{
					label: 'Benches',
					route: '/benches',
					highlight: route => {
						return this.$route.fullPath.indexOf('/benches') >= 0;
					},
					icon: FCIcons.BenchIcon
				},
				{
					label: 'Apps',
					route: '/marketplace/apps',
					highlight: route => {
						return this.$route.fullPath.indexOf('/marketplace') >= 0;
					},
					icon: FCIcons.AppsIcon,
					condition: () => this.$account.team?.is_developer
				},

				{
					label: 'Billing',
					route: '/billing',
					highlight: route => {
						return this.$route.fullPath.indexOf('/billing') >= 0;
					},
					icon: FCIcons.BillingIcon
				},
				{
					label: 'Settings',
					route: '/settings',
					highlight: route => {
						return this.$route.fullPath.indexOf('/settings') >= 0;
					},
					icon: FCIcons.SettingsIcon
				}
			].filter(d => (d.condition ? d.condition() : true));
		}
	}
};
</script>
