<template>
	<div
		class="px-5 py-10"
		v-if="$team?.doc"
		:class="{
			'h-max min-h-full sm:bg-gray-50':
				!$team.doc.onboarding.is_saas_user &&
				!$team.doc.onboarding.site_created,
		}"
	>
		<OnboardingWithoutPayment />
	</div>
</template>
<script>
import { getTeam } from '../../data/team';
import Onboarding from '../../components/Onboarding.vue';
import OnboardingWithoutPayment from '../../components/OnboardingWithoutPayment.vue';
export default {
	name: 'Welcome',
	components: {
		Onboarding,
		OnboardingWithoutPayment,
	},
	beforeRouteEnter(to, from, next) {
		let $team = getTeam();
		window.$team = $team;
		if ($team.doc.onboarding.complete && $team.doc.onboarding.site_created) {
			next({ name: 'Site List' });
		} else if (to.query.is_redirect && $team.doc.onboarding.site_created) {
			next({ name: 'Site List' });
		} else {
			next();
		}
	},
};
</script>
