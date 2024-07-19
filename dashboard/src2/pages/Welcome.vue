<template>
	<div class="px-5 py-10" v-if="$team?.doc">
		<Onboarding />
	</div>
</template>
<script>
import { getTeam } from '../data/team';
import Onboarding from '../components/Onboarding.vue';
export default {
	name: 'Welcome',
	components: {
		Onboarding
	},
	beforeRouteEnter(to, from, next) {
		let $team = getTeam();
		window.$team = $team;
		if ($team.doc.onboarding.complete && $team.doc.onboarding.site_created) {
			next({ name: 'Site List' });
		} else {
			next();
		}
	}
};
</script>
