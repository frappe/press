<template>
	<Card
		v-if="referralLink"
		title="Refer & Earn"
		subtitle="Your unique referral link"
		class="mx-auto max-w-3xl"
	>
		<div class="flex flex-col space-y-4 overflow-hidden">
			<ClickToCopyField :textContent="referralLink" />
			<span class="text-sm font-medium leading-4 text-gray-700">
				Invite someone to Frappe Cloud and
				<strong>
					get
					{{ creditAmountInTeamCurrency }} in Frappe Cloud credits</strong
				>
				when they sign up and spend at least {{ minimumSpentAmount }}!
			</span>
		</div>
	</Card>
</template>
<script>
import ClickToCopyField from '../../ClickToCopyField.vue';

export default {
	name: 'AccountReferral',
	components: {
		ClickToCopyField
	},
	computed: {
		referralLink() {
			if (this.$team.doc?.referrer_id) {
				return `${location.origin}/dashboard/signup?referrer=${this.$team.doc?.referrer_id}`;
			}
			return '';
		},
		minimumSpentAmount() {
			return this.$team.doc?.country == 'India' ? '₹1800' : '$25';
		},
		creditAmountInTeamCurrency() {
			return this.$team.doc?.country == 'India' ? '₹750' : '$10';
		}
	}
};
</script>
