<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Updates Available',
			size: '2xl',
			actions: [
				{
					label: 'Schedule Update',
					variant: 'solid',
					onClick: () => {
						return this.$site.scheduleUpdate.submit(
							{
								skip_failing_patches: this.skipFailingPatches,
								skip_backups: this.skipBackups
							},
							{
								onSuccess: () => {
									this.$site.reload();
									this.show = false;
								}
							}
						);
					}
				}
			]
		}"
	>
		<template #body-content>
			<template v-if="updatableApps.length > 0">
				<GenericList :options="listOptions" />
				<div class="mt-7 text-base text-gray-900">Update settings</div>
				<div class="mt-4 flex flex-col space-y-4">
					<FormControl
						label="Skip failing patches if any"
						type="checkbox"
						v-model="skipFailingPatches"
					/>
					<FormControl
						label="Skip backups"
						type="checkbox"
						v-model="skipBackups"
					/>
				</div>
			</template>
			<div v-else class="text-center text-base text-gray-600">
				No apps to update
			</div>
		</template>
	</Dialog>
</template>
<script>
import { FormControl, getCachedDocumentResource } from 'frappe-ui';
import GenericList from './GenericList.vue';

export default {
	name: 'SiteUpdateDialog',
	props: ['site'],
	components: {
		GenericList,
		FormControl
	},
	data() {
		return {
			show: true,
			skipFailingPatches: false,
			skipBackups: false
		};
	},
	methods: {
		twoseconds() {
			return new Promise(resolve => {
				setTimeout(() => {
					resolve();
				}, 2000);
			});
		}
	},
	computed: {
		listOptions() {
			return {
				data: this.updatableApps,
				columns: [
					{
						label: 'App',
						fieldname: 'app',
						format(value, row) {
							return row.title || value;
						}
					},
					{
						label: 'Current Version',
						type: 'Badge',
						format(value, row) {
							return row.will_branch_change
								? row.current_branch
								: row.current_tag || row.current_hash.slice(0, 7);
						},
						link(value, row) {
							if (row.will_branch_change) {
								return `${row.repository_url}/tree/${row.current_branch}`;
							}
							if (row.current_tag) {
								return `${row.repository_url}/releases/tag/${row.current_tag}`;
							}
							if (row.current_hash) {
								return `${row.repository_url}/commit/${row.current_hash}`;
							}
						}
					},
					{
						label: 'Next Version',
						type: 'Badge',
						format(value, row) {
							return row.will_branch_change
								? row.next_branch
								: row.next_tag || row.next_hash.slice(0, 7);
						},
						link(value, row) {
							if (row.will_branch_change) {
								return `${row.repository_url}/tree/${row.next_branch}`;
							}
							if (row.next_tag) {
								return `${row.repository_url}/releases/tag/${row.next_tag}`;
							}
							if (row.next_hash) {
								return `${row.repository_url}/commit/${row.next_hash}`;
							}
						}
					}
				]
			};
		},
		updatableApps() {
			if (!this.$site.doc.update_information.update_available) return [];
			let installedApps = this.$site.doc.update_information.installed_apps.map(
				d => d.app
			);
			return this.$site.doc.update_information.apps.filter(app =>
				installedApps.includes(app.app)
			);
		},
		$site() {
			return getCachedDocumentResource('Site', this.site);
		}
	}
};
</script>
