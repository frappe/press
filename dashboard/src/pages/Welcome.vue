<template>
	<div class="px-5 py-10" v-if="$team?.doc">
		<Onboarding @payment-mode-added="routeToSourcePage" />
	</div>
</template>
<script>
import { getTeam } from '../data/team';
import { getActiveSites } from '../data/sites';
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
	beforeRouteEnter: async (to, from, next) => {
		// adding to window object so that it can be accessed in mounted
		// since beforeRouteEnter is called before mounted
		window.from = from;

		let $team = getTeam();
		window.$team = $team;
		let onboarded =
			($team?.doc.onboarding.complete && $team?.doc.onboarding.site_created) ||
			(to.query.is_redirect && $team?.doc.onboarding.site_created);

		if (!onboarded) {
			next();
			return;
		}

		// only run the <3-sites quickstart check right after login only!!
		if (!to.query.post_login) {
			next({ name: 'Site List' });
			return;
		}

		let sites = getActiveSites();
		try {
			if (!sites.data) await sites.list.fetch();
		} catch (e) {
			next({ name: 'Site List' });
			return;
		}
		next({ name: sites.data.length <= 3 ? 'Quickstart' : 'Site List' });
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
