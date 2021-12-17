<template>
	<Card
		v-if="referralLink"
		title="Refer & Earn"
		subtitle="Your unique referral link"
	>
		<div class="space-y-4">
			<ClickToCopyField :textContent="referralLink" />
			<h3 class="text-base text-gray-700">
				When someone sign's up using the above link and spends at least
				{{ creditAmountInTeamCurrency }} on Frappe Cloud, you
				<strong
					>get {{ creditAmountInTeamCurrency }} in Frappe Cloud Credits</strong
				>!
			</h3>
		</div>
	</Card>
</template>
<script>
import ClickToCopyField from '@/components/ClickToCopyField.vue';

export default {
	name: 'AccountRefferal',
	components: {
		ClickToCopyField
	},
	computed: {
		referralLink() {
			if (this.$account.team.referrer_id) {
				return `${location.origin}/dashboard/signup?referrer=${this.$account.team.referrer_id}`;
			}
			return '';
		},
		creditAmountInTeamCurrency() {
			return this.$account.team.country == 'India' ? '₹1800' : '$25';
		}
	}
};
</script>
