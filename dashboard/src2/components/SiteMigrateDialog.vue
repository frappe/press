<template>
	<Dialog
		:options="{
			title: 'Migrate Database',
			actions: [
				{
					label: 'Migrate',
					variant: 'solid',
					theme: 'red',
					loading: $site.migrate.loading,
					onClick: migrate
				}
			]
		}"
		v-model="showMigrateDialog"
		@close="
			() => {
				$site.migrate.reset();
				skipFailingPatches = false;
			}
		"
	>
		<template v-slot:body-content>
			<p class="text-p-base">
				<span
					class="rounded-sm bg-gray-100 p-0.5 font-mono text-sm font-semibold"
					>bench migrate</span
				>
				command will be executed on your site. Are you sure you want to run this
				command? We recommend that you take a database backup before continuing.
			</p>
			<div class="mt-4">
				<FormControl
					type="checkbox"
					label="Skip patches if they fail during migration (Not recommended)"
					v-model="skipFailingPatches"
				/>
			</div>
			<ErrorMessage class="mt-2" :message="$site.migrate.error" />
		</template>
	</Dialog>
</template>
<script>
import { FormControl, getCachedDocumentResource } from 'frappe-ui';

export default {
	name: 'SiteMigrateDialog',
	components: { FormControl },
	props: {
		site: {
			type: String,
			required: true
		}
	},
	data() {
		return {
			showMigrateDialog: true,
			skipFailingPatches: false
		};
	},
	methods: {
		migrate() {
			this.$site.migrate.submit(
				{
					skip_failing: this.skipFailingPatches
				},
				{
					onSuccess: () => {
						this.showMigrateDialog = false;
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
