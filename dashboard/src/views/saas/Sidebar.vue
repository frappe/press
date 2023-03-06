<template>
	<div class="flex h-screen flex-col justify-between bg-gray-50 p-2">
		<div>
			<FrappeCloudLogo class="my-6 ml-2 h-4 w-auto" />
			<div
				class="mb-4 cursor-pointer rounded-xl border bg-gray-200 px-3 py-3 text-xs hover:border-gray-300"
				@click="show = true"
			>
				Search (Ctrl + k)
			</div>
			<CommandPalette :show="show" @close="show = false" />
			<router-link
				v-for="item in items"
				:key="item.label"
				:to="item.route"
				v-slot="{ href, route, navigate }"
			>
				<a
					:class="[
						(
							Boolean(item.highlight)
								? item.highlight(route)
								: item.route == '/'
						)
							? 'bg-gray-200'
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
		<Dropdown
			placement="center"
			:options="dropdownItems"
		>
			<template v-slot="{ open }">
				<div
					class="m-2 flex cursor-pointer items-center gap-2 rounded-md p-2 truncate break-all"
					:class="open ? 'bg-gray-300' : 'hover:bg-gray-200'"
				>
					<Avatar
						v-if="$account.user"
						:label="$account.user.first_name"
						:imageURL="$account.user.user_image"
					/>

					<div v-if="$account.user">
						<h3 class="text-base font-semibold">
							{{ $account.user.full_name }}
						</h3>
						<p class="text-xs text-gray-600">{{ $account.user.email }}</p>
					</div>
				</div>
			</template>
		</Dropdown>
	</div>
</template>

<script>
import { FCIcons } from '@/components/icons';
import FrappeCloudLogo from '@/components/FrappeCloudLogo.vue';
import CommandPalette from '@/components/CommandPalette.vue';

export default {
	name: 'Sidebar',
	components: {
		FrappeCloudLogo,
		CommandPalette
	},
	data() {
		return {
			show: false,
			dropdownItems: [
				{
					label: 'Docs',
					icon: 'book-open',
					handler: () => (window.location.href = '/docs')
				},
				{
					label: 'Support',
					icon: 'help-circle',
					handler: () => (window.location.href = '/support')
				},
				{
					label: 'Settings',
					icon: 'settings',
					handler: () => this.$router.push('/settings')
				},
				{
					label: 'Logout',
					icon: 'log-out',
					handler: () => this.$auth.logout()
				}
			]
		};
	},
	mounted() {
		window.addEventListener('keydown', e => {
			if (e.key === 'k' && (e.ctrlKey || e.metaKey)) {
				this.show = !this.show;
				e.preventDefault();
			}
			if (e.key === 'Escape') {
				this.show = false;
			}
		});
	},
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
					label: 'Servers',
					route: '/servers',
					highlight: route => {
						return this.$route.fullPath.indexOf('/servers') >= 0;
					},
					icon: FCIcons.ServerIcon,
					condition: () => this.$account.team?.servers_enabled
				},
				{
					label: 'Developer',
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
