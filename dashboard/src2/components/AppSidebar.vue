<template>
	<div
		class="relative flex min-h-screen w-[220px] flex-col border-r bg-gray-50"
	>
		<div class="p-2">
			<Dropdown
				:options="[
					{
						label: 'Change Team',
						icon: 'command',
						onClick: () => (showTeamSwitcher = true)
					},
					{
						label: 'Support & Docs',
						icon: 'help-circle',
						onClick: support
					},
					{
						label: 'Share Feedback',
						icon: 'file-text',
						onClick: feedback
					},
					{
						label: 'Logout',
						icon: 'log-out',
						onClick: $session.logout.submit
					}
				]"
			>
				<template v-slot="{ open }">
					<button
						class="flex w-[204px] items-center rounded-md px-2 py-2 text-left"
						:class="open ? 'bg-white shadow-sm' : 'hover:bg-gray-200'"
					>
						<FCLogo class="h-8 w-8 shrink-0 rounded" />
						<div class="ml-2 flex flex-1 flex-col overflow-hidden">
							<div class="text-base font-medium leading-none text-gray-900">
								Frappe Cloud
							</div>
							<Tooltip :text="$team?.doc?.user || null">
								<div
									class="mt-1 hidden overflow-hidden text-ellipsis whitespace-nowrap text-sm leading-none text-gray-700 sm:inline"
								>
									{{ $team?.get.loading ? 'Loading...' : $team.doc.user }}
								</div>
							</Tooltip>
						</div>
						<FeatherIcon
							name="chevron-down"
							class="ml-auto h-5 w-5 text-gray-700"
						/>
					</button>
				</template>
			</Dropdown>
		</div>
		<nav class="px-2">
			<NavigationItems>
				<template v-slot="{ navigation }">
					<template v-for="(item, i) in navigation">
						<template v-if="item.items">
							<div
								class="py-1 text-sm leading-5 text-gray-600"
								:class="{ 'mt-2': i != 0 }"
							>
								{{ item.name }}
							</div>
							<div class="space-y-0.5">
								<AppSidebarItem
									v-for="subItem in item.items"
									:key="subItem.name"
									:item="subItem"
								/>
							</div>
						</template>
						<AppSidebarItem
							class="mt-0.5"
							v-else
							:key="item.name"
							:item="item"
						/>
					</template>
				</template>
			</NavigationItems>
		</nav>
		<div class="mt-auto p-2">
			<Button variant="ghost" @click="switchToOldDashboard">
				Switch to old dashboard
			</Button>
		</div>
		<!-- TODO: update component name after dashboard-beta merges -->
		<SwitchTeamDialog2 v-model="showTeamSwitcher" />
	</div>
</template>

<script>
import { defineAsyncComponent } from 'vue';
import AppSidebarItem from './AppSidebarItem.vue';
import { Tooltip } from 'frappe-ui';
import NavigationItems from './NavigationItems.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'AppSidebar',
	components: {
		AppSidebarItem,
		SwitchTeamDialog2: defineAsyncComponent(() =>
			import('./SwitchTeamDialog.vue')
		),
		Tooltip,
		NavigationItems
	},
	data() {
		return {
			showTeamSwitcher: false
		};
	},
	methods: {
		support() {
			window.open('https://frappecloud.com/support', '_blank');
		},
		feedback() {
			window.open(
				'https://frappecloud.com/frappe-cloud-feedback/new',
				'_blank'
			);
		},
		switchToOldDashboard() {
			toast.promise(
				this.$team.changeDefaultDashboard.submit(
					{ new_dashboard: false },
					{
						onSuccess() {
							window.location.href = '/dashboard';
						}
					}
				),
				{
					loading: 'Switching to old dashboard...',
					success: () => 'Switching to old dashboard...',
					error: e => 'Failed to switch to old dashboard'
				}
			);
		}
	}
};
</script>
