<template>
	<div class="px-5 py-10" v-if="$team?.doc">
		<Onboarding />
	</div>
</template>
<script>
import Onboarding from '../components/Onboarding.vue';
export default {
	name: 'Welcome',
	components: {
		Onboarding
	}
};
</script>
