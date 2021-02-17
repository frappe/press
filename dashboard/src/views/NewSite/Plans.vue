<template>
	<div>
		<label class="text-lg font-semibold">
			Choose your plan
		</label>
		<p class="text-base text-gray-700">
			Select a plan based on the type of usage you are expecting on your site.
		</p>
		<div class="mt-4">
			<Alert class="mb-4" v-if="showAlert">
				You have not added your billing information.
				<router-link to="/welcome" class="border-b border-yellow-500">
					Add your billing information
				</router-link>
				to create sites.
			</Alert>
			<SitePlansTable
				:plans="options.plans"
				:selectedPlan="selectedPlan"
				@change="plan => $emit('update:selectedPlan', plan)"
			/>
		</div>
	</div>
</template>
<script>
import SitePlansTable from '@/components/SitePlansTable';
export default {
	name: 'Plans',
	props: ['options', 'selectedPlan'],
	components: {
		SitePlansTable
	},
	computed: {
		showAlert() {
			return (
				this.options &&
				!this.options.free_account &&
				!this.options.has_card &&
				!this.options.allow_partner
			);
		}
	}
};
</script>
