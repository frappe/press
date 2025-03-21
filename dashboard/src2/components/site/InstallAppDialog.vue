<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Install app on your site',
			size: '4xl',
		}"
	>
		<template #body-content>
			<ObjectList :options="listOptions" />
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import { defineAsyncComponent, h } from 'vue';
import { toast } from 'vue-sonner';
import { renderDialog } from '../../utils/components';
import router from '../../router';
import ObjectList from '../ObjectList.vue';
import { getToastErrorMessage } from '../../utils/toast';

export default {
	props: {
		site: {
			type: String,
			required: true,
		},
	},
	emits: ['installed'],
	components: {
		ObjectList,
	},
	data() {
		return {
			show: true,
		};
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
		listOptions() {
			const handleInstall = (row) => {
				if (this.$site.installApp.loading) return;

				if (row.plans && row.plans.some((plan) => plan.price_inr > 0)) {
					this.show = false;

					let SiteAppPlanSelectDialog = defineAsyncComponent(
						() => import('./SiteAppPlanSelectDialog.vue'),
					);

					renderDialog(
						h(SiteAppPlanSelectDialog, {
							app: row,
							currentPlan: null,
							onPlanSelected: (plan) => {
								toast.promise(
									this.$site.installApp.submit({
										app: row.app,
										plan: plan.name,
									}),
									{
										loading: 'Installing app...',
										success: (jobId) => {
											router.push({
												name: 'Site Job',
												params: {
													name: this.site,
													id: jobId,
												},
											});
											this.$emit('installed');
											this.show = false;
											return 'App will be installed shortly';
										},
										error: (e) => getToastErrorMessage(e),
									},
								);
							},
						}),
					);
				} else {
					toast.promise(
						this.$site.installApp.submit({
							app: row.app,
						}),
						{
							loading: 'Installing app...',
							success: (jobId) => {
								router.push({
									name: 'Site Job',
									params: {
										name: this.site,
										id: jobId,
									},
								});
								this.$emit('installed');
								this.show = false;
								return 'App will be installed shortly';
							},
							error: (e) => getToastErrorMessage(e),
						},
					);
				}
			};
			return {
				label: 'App',
				fieldname: 'app',
				fieldtype: 'ListSelection',
				emptyStateMessage:
					'No apps found' +
					(!this.$site.doc?.group_public
						? '. Please add them from your bench.'
						: ''),
				columns: [
					{
						label: 'Title',
						fieldname: 'title',
						class: 'font-medium',
						width: 2,
						format: (value, row) => value || row.app_title,
					},
					{
						label: 'Repo',
						fieldname: 'repository_owner',
						class: 'text-gray-600',
						width: '10rem',
					},
					{
						label: 'Branch',
						fieldname: 'branch',
						class: 'text-gray-600',
						width: '20rem',
					},
					{
						label: '',
						fieldname: '',
						align: 'right',
						type: 'Button',
						width: '5rem',
						Button({ row }) {
							return {
								label: 'Install',
								onClick: () => {
									handleInstall(row);
								},
							};
						},
					},
				],
				resource: () => {
					return {
						url: 'press.api.site.available_apps',
						params: {
							name: this.site,
						},
						auto: true,
					};
				},
			};
		},
	},
};
</script>
