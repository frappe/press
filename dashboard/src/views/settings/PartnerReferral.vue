<template>
	<Card
		title="Partner Referral"
		subtitle="Your unique partner referral code"
		v-if="$account.team.erpnext_partner"
	>
		<div class="space-y-4">
			<ClickToCopyField :textContent="referralCode" />
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
