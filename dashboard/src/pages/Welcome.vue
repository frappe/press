<template>
	<div class="px-5 py-10" v-if="$team?.doc">
		<Onboarding @payment-mode-added="routeToSourcePage" />
	</div>
</template>
<script>
import { getTeam } from '../data/team';
import Onboarding from '../components/Onboarding.vue';
import OnboardingWithoutPayment from '../components/OnboardingWithoutPayment.vue';
export default {
	name: 'Welcome',
	components: {
		Onboarding,
		OnboardingWithoutPayment,
	},
	data() {
		return {
			from: {},
		};
	},
	mounted() {
		this.from = window.from;
	},
	beforeRouteEnter: (to, from, next) => {
		// adding to window object so that it can be accessed in mounted
		// since beforeRouteEnter is called before mounted
		window.from = from;

		let $team = getTeam();
		window.$team = $team;
		if ($team?.doc.onboarding.complete && $team?.doc.onboarding.site_created) {
			next({ name: 'Site List' });
		} else if (to.query.is_redirect && $team?.doc.onboarding.site_created) {
			next({ name: 'Site List' });
		} else {
			next();
		}
	},
	methods: {
		routeToSourcePage() {
			if (this.from.name) {
				this.$router.push({ name: this.from.name, params: this.from.params });
			} else {
				this.$router.push({ name: 'Site List' });
			}
		},
	},
};
</script>
