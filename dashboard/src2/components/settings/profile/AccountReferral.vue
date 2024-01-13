<template>
	<Card
		v-if="referralLink"
		title="Refer & Earn"
		subtitle="Your unique referral link"
	>
		<div class="space-y-4 overflow-hidden">
			<ClickToCopyField :textContent="referralLink" />
			<h3 class="text-base text-gray-700">
				When someone sign's up using the above link and spends at least
				{{ minimumSpentAmount }} on Frappe Cloud, you
				<strong>
					get {{ creditAmountInTeamCurrency }} in Frappe Cloud Credits!
				</strong>
			</h3>
		</div>
	</Card>
</template>
<script>
import ClickToCopyField from '@/components/ClickToCopyField.vue';
import { getTeam } from '../../../data/team';

export default {
	name: 'AccountRefferal',
	components: {
		ClickToCopyField
	},
	computed: {
		team() {
			return getTeam()?.doc;
		},
		referralLink() {
			if (this.team.referrer_id) {
				return `${location.origin}/dashboard/signup?referrer=${this.team.referrer_id}`;
			}
			return '';
		},
		minimumSpentAmount() {
			return this.team.country == 'India' ? '₹1800' : '$25';
		},
		creditAmountInTeamCurrency() {
			return this.team.country == 'India' ? '₹750' : '$10';
		}
	}
};
</script>
