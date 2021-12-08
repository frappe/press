<template>
	<Card
		v-if="referralLink"
		title="Refer & Earn"
		subtitle="Your unique referral link"
	>
		<div class="space-y-4">
			<div
				class="p-2 items-center rounded-lg flex flex-row border-2 justify-between"
			>
				<p class="text-sm text-gray-800 font-mono overflow-hidden">
					{{ referralLink }}
				</p>
				<Button icon="copy" @click="copyReferralLink" />
			</div>
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
export default {
	name: 'AccountRefferal',
	methods: {
		copyReferralLink() {
			const clipboard = window.navigator.clipboard;
			clipboard.writeText(this.referralLink).then(() => {
				this.$notify({
					title: 'Link copied to clipboard!',
					icon: 'check',
					color: 'green'
				});
			});
		}
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
