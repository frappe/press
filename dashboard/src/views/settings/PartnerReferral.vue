<template>
	<Card
		title="Partner Referral"
		subtitle="Your unique partner referral code"
		v-if="$account.team.erpnext_partner"
	>
		<div class="space-y-4">
			<ClickToCopyField :textContent="referralCode" />
			<h3 class="text-base text-gray-700">
				Partners can share this referral code with their customers to link their
				account with the partner.
			</h3>
		</div>
	</Card>
</template>

<script>
import ClickToCopyField from '@/components/ClickToCopyField.vue';

export default {
	name: 'PartnerReferral',
	components: {
		ClickToCopyField
	},
	computed: {
		referralCode() {
			if (
				this.$account.team.erpnext_partner &&
				this.$account.team.partner_referral_code
			) {
				return this.$account.team.partner_referral_code;
			}
			return '';
		}
	}
};
</script>
