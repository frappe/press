<template>
	<Dialog
		:options="{
			title: 'Reset Database',
			actions: [
				{
					label: 'Reset',
					variant: 'solid',
					theme: 'red',
					loading: $site.reinstall.loading,
					onClick: reset
				}
			]
		}"
		v-model="showDialog"
	>
		<template v-slot:body-content>
			<p class="text-p-base">
				All the data from your site will be lost. Are you sure you want to reset
				your database?
			</p>
			<p class="mt-4 text-sm">
				Please type
				<span class="font-semibold">{{ $site.name }}</span> to confirm.
			</p>
			<FormControl
				class="mt-1.5 w-full"
				v-model="confirmSiteName"
				autocomplete="off"
			/>
			<ErrorMessage class="mt-2" :message="$site.reinstall.error" />
		</template>
	</Dialog>
</template>
<script>
import { FormControl, getCachedDocumentResource } from 'frappe-ui';

export default {
	name: 'SiteResetDialog',
	components: { FormControl },
	props: {
		site: {
			type: String,
			required: true
		}
	},
	data() {
		return {
			showDialog: true,
			confirmSiteName: ''
		};
	},
	methods: {
		reset() {
			this.$site.reinstall.submit(
				{},
				{
					validate: () => {
						if (this.confirmSiteName !== this.$site.name) {
							return 'Please type the site name to confirm.';
						}
					},
					onSuccess: () => {
						this.showDialog = false;
						this.$router.push({
							name: 'Site Detail Jobs',
							params: { objectType: 'Site', name: this.site }
						});
					}
				}
			);
		}
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		}
	}
};
</script>
