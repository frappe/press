<template>
	<div>
		<header class="sticky top-0 z-10 border-b bg-white px-5 pt-2.5">
			<Breadcrumbs
				:items="[{ label: 'Settings', route: { name: 'SettingsScreen' } }]"
			/>
			<Tabs :tabs="tabs" class="-mb-px pl-0.5" />
		</header>
		<div class="mx-auto max-w-4xl py-5">
			<router-view />
		</div>
	</div>
</template>

<script>
import PageHeader from '@/components/PageHeader.vue';
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
				{
					label: 'Team',
					route: 'team',
					condition: () => $account.user.name === $account.team.user
				},
				{ label: 'Developer', route: 'developer' },
				{ label: 'Partner', route: 'partner' }
			].filter(tab => (tab.condition ? tab.condition() : true));

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

			if (team.name !== user.name) {
				if (team.team_title) subtitle += `Team: ${team.team_title}`;
				else subtitle += `Team: ${team.name}`;
				subtitle += ` &middot; Member: ${user.name} `;
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
