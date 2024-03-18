<template>
	<div class="space-y-12">
		<div v-if="publicApps">
			<h2 class="text-sm font-medium leading-6 text-gray-900">
				Select Marketplace Apps
			</h2>
			<div class="mt-2 w-full space-y-2">
				<ObjectList :options="publicApps" />
			</div>
			<SiteAppPlanSelectorDialog
				v-if="selectedApp"
				v-model="showAppPlanSelectorDialog"
				:app="selectedApp"
				@plan-select="
					plan => {
						apps = [...apps, { app: selectedApp.app, plan }];
						showAppPlanSelectorDialog = false;
					}
				"
			/>
		</div>
		<div v-if="!siteOnPublicBench && privateApps">
			<h2 class="text-sm font-medium leading-6 text-gray-900">
				Select Private Apps
			</h2>
			<div class="mt-2 w-full space-y-2">
				<ObjectList :options="privateApps" />
			</div>
		</div>
	</div>
</template>

<script>
import { h } from 'vue';
import DownloadIcon from '~icons/lucide/download';
import SiteAppPlanSelectorDialog from './SiteAppPlanSelectorDialog.vue';
import { Badge } from 'frappe-ui';
import { icon } from '../../utils/components';
import ObjectList from '../ObjectList.vue';

export default {
	props: ['availableApps', 'siteOnPublicBench', 'modelValue'],
	emits: ['update:modelValue'],
	components: {
		ObjectList,
		SiteAppPlanSelectorDialog
	},
	data() {
		return {
			selectedApp: null,
			showAppPlanSelectorDialog: false
		};
	},
	computed: {
		apps: {
			get() {
				return this.modelValue || [];
			},
			set(newApps) {
				this.$emit('update:modelValue', newApps);
			}
		},
		publicApps() {
			if (!this.availableApps) return;
			let publicApps = this.availableApps.filter(
				app => (app.public || app.plans?.length) && app.image
			);

			if (!publicApps.length) return;

			return {
				data: () => publicApps,
				columns: [
					{
						label: 'App',
						fieldname: 'app_title',
						width: 0.5,
						type: 'Component',
						component: ({ row }) => {
							return h(
								'a',
								{
									class: 'flex items-center text-sm',
									href: `/${row.route}`,
									target: '_blank'
								},
								[
									h('img', {
										class: 'h-6 w-6',
										src: row.image
									}),
									h('span', { class: 'ml-2' }, row.app_title)
								]
							);
						}
					},
					{
						label: 'Installs',
						width: 0.2,
						type: 'Component',
						component: ({ row }) => {
							return h(
								'div',
								{
									class: 'flex items-center text-sm text-gray-600'
								},
								[
									h(DownloadIcon, {
										class: 'h-3 w-3'
									}),
									h('span', { class: 'ml-0.5 leading-3' }, [
										this.$format.numberK(row.total_installs || '')
									])
								]
							);
						}
					},
					{
						label: 'Subscription',
						width: 0.2,
						type: 'Component',
						component: ({ row }) => {
							if (row.subscription_type !== 'Free')
								return h(Badge, {
									theme: 'gray',
									label: 'Paid'
								});
						}
					},
					{
						label: '',
						width: 0.2,
						align: 'right',
						type: 'Button',
						Button: ({ row: app }) => {
							let formatPlan = plan => {
								let price = plan.price_usd;
								return price > 0 ? `$${price}` : 'Free';
							};

							let plan = this.apps.find(a => a.app === app.app)?.plan;
							let title = plan ? formatPlan(plan) : 'Free';
							let isAppAdded = this.apps.map(a => a.app).includes(app.app);

							return {
								label: isAppAdded ? title : 'Add',
								slots: {
									prefix: isAppAdded ? icon('check') : icon('plus')
								},
								variant: isAppAdded ? 'outline' : 'subtle',
								onClick: event => {
									this.toggleApp(app);
									event.stopPropagation();
								}
							};
						}
					}
				]
			};
		},
		privateApps() {
			if (!this.availableApps) return;

			let privateApps = this.availableApps.filter(
				app => !((app.public || app.plans?.length) && app.image)
			);

			if (privateApps.length === 0) return;

			return {
				data: () => privateApps,
				columns: [
					{
						label: 'App',
						fieldname: 'app_title'
					},
					{
						label: '',
						align: 'right',
						type: 'Button',
						Button: ({ row: app }) => {
							return {
								label: this.apps
									.map(a => a.app)
									.includes(app.app || app.app_title)
									? 'Added'
									: 'Add',
								slots: {
									prefix: this.apps
										.map(a => a.app)
										.includes(app.app || app.app_title)
										? icon('check')
										: icon('plus')
								},
								variant: this.apps.map(a => a.app).includes(app.app)
									? 'outline'
									: 'subtle',
								onClick: event => {
									this.toggleApp(app);
									event.stopPropagation();
								}
							};
						}
					}
				]
			};
		}
	},
	methods: {
		toggleApp(app) {
			if (this.apps.map(a => a.app).includes(app.app)) {
				this.apps = this.apps.filter(a => a.app !== app.app);
			} else {
				if (app.subscription_type && app.subscription_type !== 'Free') {
					this.selectedApp = app;
					this.showAppPlanSelectorDialog = true;
				} else {
					this.apps = [...this.apps, app];
				}
			}
		}
	}
};
</script>
