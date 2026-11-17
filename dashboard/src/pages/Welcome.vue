<template>
	<div class="flex flex-col gap-5 px-5 py-10" v-if="$team?.doc">
		<Onboarding @payment-mode-added="routeToSourcePage" />
		<!-- Self-hosters sign up only for the warranty, so they need a way to it from here. -->
		<SelfHostedCard v-if="canOrderWarranty" />
	</div>
</template>
<script>
import SelfHostedCard from '../components/enterprise-contract/SelfHostedCard.vue'
import Onboarding from '../components/Onboarding.vue'
import OnboardingWithoutPayment from '../components/OnboardingWithoutPayment.vue'
import { session } from '../data/session'
import { getTeam } from '../data/team'
export default {
	name: 'Welcome',
	components: {
		Onboarding,
		OnboardingWithoutPayment,
		SelfHostedCard,
	},
	computed: {
		canOrderWarranty() {
			return session.hasBillingAccess && !this.$team.doc.erpnext_partner
		},
	},
	data() {
		return {
			from: {},
		}
	},
	mounted() {
		this.from = window.from
	},
	beforeRouteEnter: (to, from, next) => {
		// adding to window object so that it can be accessed in mounted
		// since beforeRouteEnter is called before mounted
		window.from = from

		let $team = getTeam()
		window.$team = $team
		let onboarded =
			($team?.doc.onboarding.complete && $team?.doc.onboarding.site_created) ||
			(to.query.is_redirect && $team?.doc.onboarding.site_created)

		if (onboarded) {
			next({ name: 'Site List' })
			return
		}

		next()
	},
	methods: {
		routeToSourcePage() {
			if (this.from.name) {
				this.$router.push({ name: this.from.name, params: this.from.params })
			} else {
				this.$router.push({ name: 'Site List' })
			}
		},
	},
}
</script>
