<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<BreadCrumbs
				:items="[{ label: 'Settings', route: { name: 'SettingsScreen' } }]"
			/>
		</header>
		<PageHeader class="mx-5 mt-3" title="Settings" :subtitle="pageSubtitle" />
		<Tabs class="mx-5" :tabs="tabs">
			<router-view v-slot="{ Component, route }">
				<component :is="Component"></component>
			</router-view>
		</Tabs>
	</div>
</template>

<script>
import PageHeader from '@/components/global/PageHeader.vue';
import Tabs from '@/components/Tabs.vue';

export default {
	name: 'AccountSettings',
	pageMeta() {
		return {
			title: 'Settings - Profile'
		};
	},
	components: {
		Tabs,
		PageHeader
	},
	computed: {
		tabs() {
			let tabRoute = subRoute => `/settings/${subRoute}`;
			let tabs = [
				{ label: 'Profile', route: 'profile' },
				{ label: 'Team', route: 'team' },
				{ label: 'Billing', route: 'billing' }
			];

			return tabs.map(tab => {
				return {
					...tab,
					route: tabRoute(tab.route)
				};
			});
		},
		pageSubtitle() {
			const { user, team } = this.$account;
			let subtitle = '';

			if (!user || !team) {
				return subtitle;
			}

			if (team.name != user.name) {
				subtitle += `Team: ${team.name} &middot; Member: ${user.name} `;
			} else {
				subtitle += `<span>${team.name}</span> `;
			}

			if (team.erpnext_partner) {
				subtitle += `&middot; <span>ERPNext Partner</span>`;
			}

			let userTeamMember = team.team_members.filter(
				member => member.user === user.name
			);

			if (userTeamMember.length > 0) {
				userTeamMember = userTeamMember[0];
				const memberSince = this.$date(userTeamMember.creation).toLocaleString({
					month: 'short',
					day: 'numeric',
					year: 'numeric'
				});
				subtitle += `&middot; <span>Member since ${memberSince}</span>`;
			}

			return subtitle;
		}
	}
};
</script>
