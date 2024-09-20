<template>
	<div v-if="$site.doc.current_plan.monitor_access" class="m-5">
		<ObjectList :options="processListOptions" />
	</div>
	<div class="flex justify-center" v-else>
		<span class="mt-16 text-base text-gray-700">
			Your plan doesn't support this feature. Please
			<span class="cursor-pointer underline" @click="showPlanChangeDialog"
				>upgrade your plan</span
			>
			.
		</span>
	</div>
</template>
<script>
import { getCachedDocumentResource } from 'frappe-ui';
import { defineAsyncComponent, h } from 'vue';
import { renderDialog } from '../../../utils/components';
import ObjectList from '../../ObjectList.vue';

export default {
	name: 'SiteMariaDBProcessList',
	props: ['name'],
	components: {
		ObjectList
	},
	methods: {
		showPlanChangeDialog() {
			const SitePlansDialog = defineAsyncComponent(() =>
				import('../../ManageSitePlansDialog.vue')
			);
			renderDialog(h(SitePlansDialog, { site: this.name }));
		}
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.name);
		},
		processListOptions() {
			return {
				resource: () => {
					return {
						url: 'press.api.analytics.mariadb_processlist',
						params: {
							site: this.name
						},
						auto: true,
						initialData: []
					};
				},
				columns: [
					{
						label: 'ID',
						fieldname: 'Id',
						width: '6rem'
					},
					{
						label: 'User',
						fieldname: 'User',
						width: '15rem'
					},
					{
						label: 'Time',
						fieldname: 'Time',
						width: '6rem'
					},
					{
						label: 'Command',
						fieldname: 'Command',
						width: '6rem'
					},
					{
						label: 'State',
						fieldname: 'State',
						width: '8rem'
					},
					{
						label: 'Query',
						fieldname: 'Info',
						class: 'font-mono'
					}
				],
				actions: () => {
					return [
						{
							label: 'Back',
							icon: 'arrow-left',
							onClick: () => {
								this.$router.push({ name: 'Site Detail Performance' });
							}
						}
					];
				}
			};
		}
	}
};
</script>
