<template>
	<div>
		<PageHeader title="Settings" :subtitle="pageSubtitle" />
		<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
			<AccountProfile />
			<AccountTeam />
			<AccountMembers />
			<AccountActions />
			<AccountReferral />
			<AccountEmails />
			<AccountAPI />
			<AccountSSHKey />
		</div>
	</div>
</template>

<script>
import AccountProfile from './AccountProfile.vue';
import AccountTeam from './AccountTeam.vue';
import AccountMembers from './AccountMembers.vue';
import AccountActions from './AccountActions.vue';
import AccountReferral from './AccountReferral.vue';
import AccountEmails from './AccountEmails.vue';
import AccountAPI from './AccountAPI.vue';
import AccountSSHKey from './AccountSSHKey.vue';
import PageHeader from '@/components/global/PageHeader.vue';

export default {
	name: 'AccountSettings',
	pageMeta() {
		return {
			title: 'Settings - Frappe Cloud'
		};
	},
	components: {
		AccountActions,
		AccountProfile,
		AccountTeam,
		AccountMembers,
		AccountReferral,
		AccountEmails,
		AccountAPI,
		AccountSSHKey,
		PageHeader
	},
	computed: {
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
