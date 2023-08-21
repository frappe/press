<template>
	<div class="flex h-screen flex-col justify-between bg-gray-50 p-2">
		<div>
			<Dropdown :options="dropdownItems">
				<template v-slot="{ open }">
					<div
						class="flex w-[15rem] cursor-pointer items-center gap-2 rounded-md px-2 py-2"
						:class="open ? 'bg-white shadow-sm' : 'hover:bg-gray-200'"
					>
						<div>
							<FrappeCloudLogo class="h-5" />
							<p
								v-if="$account.user"
								class="mt-1 break-all text-sm text-gray-600"
							>
								{{ $account.user.full_name }}
							</p>
						</div>
						<FeatherIcon
							name="chevron-down"
							class="ml-auto h-5 w-5 text-gray-700"
						/>
					</div>
				</template>
			</Dropdown>
			<div class="mt-2 flex flex-col space-y-0.5">
				<button
					class="rounded text-gray-900 hover:bg-gray-100"
					@click="show = true"
				>
					<div class="flex w-full items-center px-2 py-1">
						<span class="mr-1.5">
							<FeatherIcon name="search" class="h-5 w-5 text-gray-700" />
						</span>
						<span class="text-sm">Search</span>
						<span class="ml-auto text-sm text-gray-500">
							<template v-if="$platform === 'mac'">⌘K</template>
							<template v-else>Ctrl+K</template>
						</span>
					</div>
				</button>
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
								? 'bg-white shadow-sm'
								: 'text-gray-900 hover:bg-gray-100'
						]"
						:href="href"
						@click="navigate"
						class="flex items-center rounded-md px-2 py-1 pr-10 text-start text-sm focus:outline-none"
					>
						<Component class="mr-1.5 text-gray-700" :is="item.icon" />
						{{ item.label }}
					</a>
				</router-link>
			</div>
		</div>
		<SwitchTeamDialog v-model="showTeamSwitcher" />
	</div>
</template>

<script>
import { FCIcons } from '@/components/icons';
import SwitchTeamDialog from './SwitchTeamDialog.vue';
import FrappeCloudLogo from '@/components/icons/FrappeCloudLogo.vue';
import CommandPalette from '@/components/CommandPalette.vue';

export default {
	name: 'Sidebar',
	components: {
		FrappeCloudLogo,
		SwitchTeamDialog,
		CommandPalette
	},
	data() {
		return {
			show: false,
			showTeamSwitcher: false,
			dropdownItems: [
				{
					label: 'Switch Team',
					icon: 'command',
					onClick: () => (this.showTeamSwitcher = true)
				},
				{
					label: 'Support & Docs',
					icon: 'help-circle',
					onClick: () => (window.location.href = '/support')
				},
				{
					label: 'Settings',
					icon: 'settings',
					onClick: () => this.$router.push('/settings/profile')
				},
				{
					label: 'Logout',
					icon: 'log-out',
					onClick: () => this.$auth.logout()
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
					highlight: () => {
						return (
							this.$route.fullPath.indexOf('/sites') >= 0 &&
							this.$route.fullPath.indexOf('/benches/') < 0
						);
					},
					icon: FCIcons.SiteIcon
				},
				{
					label: 'Benches',
					route: '/benches',
					highlight: () => {
						return (
							this.$route.fullPath.indexOf('/benches') >= 0 &&
							this.$route.fullPath.indexOf('/servers/') < 0
						);
					},
					icon: FCIcons.BenchIcon
				},
				{
					label: 'Servers',
					route: '/servers',
					highlight: () => {
						return this.$route.fullPath.indexOf('/servers') >= 0;
					},
					icon: FCIcons.ServerIcon,
					condition: () => this.$account.team?.servers_enabled
				},
				{
					label: 'Spaces',
					route: '/spaces',
					highlight: () => {
						return this.$route.fullPath.indexOf('/spaces') >= 0;
					},
					icon: FCIcons.SpacesIcon,
					condition: () => this.$account.team?.code_servers_enabled
				},
				{
					label: 'Apps',
					route: '/marketplace/apps',
					highlight: () => {
						return this.$route.fullPath.indexOf('/marketplace') >= 0;
					},
					icon: FCIcons.AppsIcon,
					condition: () => this.$account.team?.is_developer
				},
				{
					label: 'Security',
					route: '/security',
					highlight: () => {
						return this.$route.fullPath.indexOf('/security') >= 0;
					},
					icon: FCIcons.SecurityIcon,
					condition: () => this.$account.team?.security_portal_enabled
				},
				{
					label: 'Settings',
					route: '/settings',
					highlight: () => {
						return (
							this.$route.fullPath.indexOf('/settings') >= 0 &&
							this.$route.fullPath.indexOf('/sites/') < 0 &&
							this.$route.fullPath.indexOf('/benches/') < 0 &&
							this.$route.fullPath.indexOf('/servers/') < 0
						);
					},
					icon: FCIcons.SettingsIcon
				}
			].filter(d => (d.condition ? d.condition() : true));
		}
	}
};
</script>
