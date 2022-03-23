<template>
	<Dialog v-if="showDialog" v-model="showDialog" title="Update Country">
		Please select your country

		<select
			class="form-select mt-2 block w-full shadow"
			v-model="country"
			name="country"
			autocomplete="country"
		>
			<option v-for="country in countries" :key="country.name">
				{{ country.name }}
			</option>
		</select>

		<template v-slot:actions>
			<Button
				:disabled="state === 'RequestStarted'"
				type="primary"
				@click="submit"
			>
				Submit
			</Button>
		</template>
	</Dialog>
</template>

<script>
export default {
	data() {
		return {
			state: null,
			errorMessage: null,
			showDialog: false,
			country: null,
			countries: []
		};
	},
	async mounted() {
		this.$account.$watch('team', async team => {
			if (team && !team.country && this.$account.hasRole('Press Admin')) {
				await this.fetchCountries();
				this.showDialog = true;
			}
		});
	},
	methods: {
		async fetchCountries() {
			this.countries = await this.$call('press.api.account.country_list');
		},
		async submit() {
			await this.$call('press.api.account.set_country', {
				country: this.country
			});
			this.showDialog = false;
		}
	}
};
</script>
