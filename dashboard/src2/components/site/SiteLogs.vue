<template>
	<ObjectList class="p-5" :options="logsOptions" />
</template>

<script>
import { date } from '../../utils/format';
import ObjectList from '../ObjectList.vue';

export default {
	name: 'SiteLogs',
	props: {
		name: {
			type: String,
			required: true
		},
		type: {
			type: String,
			required: false
		}
	},
	components: {
		ObjectList
	},
	resources: {
		logs() {
			return {
				url: 'press.api.site.logs',
				params: {
					name: this.name
				},
				auto: true,
				initialData: [],
				cache: ['ObjectList', 'press.api.site.logs', this.name]
			};
		}
	},
	computed: {
		logs() {
			const knownTypes = [
				'frappe',
				'scheduler',
				'database',
				'pdf',
				'wkhtmltopdf',
				'ipython'
			];

			if (this.type && !knownTypes.includes(this.type)) {
				return this.$resources.logs.data.filter(
					d => !knownTypes.includes(d.name.split('.')[0])
				);
			}

			// logs of a particular type
			return this.$resources.logs.data.filter(
				d => d.name.split('.')[0] === this.type
			);
		},
		logsOptions() {
			if (this.type) {
				return {
					data: () => this.logs,
					route(row) {
						return {
							name: 'Site Log',
							params: { logName: row.name }
						};
					},
					columns: [
						{
							label: 'Name',
							fieldname: 'name'
						},
						{
							label: 'Size',
							fieldname: 'size',
							class: 'text-gray-600',
							format(value) {
								return `${value} kB`;
							}
						},
						{
							label: 'Created On',
							fieldname: 'created',
							format(value) {
								return value ? date(value, 'lll') : '';
							}
						},
						{
							label: 'Modified On',
							fieldname: 'modified',
							format(value) {
								return value ? date(value, 'lll') : '';
							}
						}
					],
					actions: () => [
						{
							label: 'Refresh',
							icon: 'refresh-ccw',
							loading: this.$resources.logs.loading,
							onClick: () => this.$resources.logs.reload()
						}
					]
				};
			} else {
				return {
					data: () => [
						{
							title: 'Scheduler Logs',
							route: {
								name: 'Site Logs',
								params: {
									name: this.name,
									type: 'scheduler'
								}
							}
						},
						{
							title: 'Database Logs',
							route: {
								name: 'Site Logs',
								params: {
									name: this.name,
									type: 'database'
								}
							}
						},
						{
							title: 'Frappe Logs',
							route: {
								name: 'Site Logs',
								params: {
									name: this.name,
									type: 'frappe'
								}
							}
						},
						{
							title: 'PDF Logs',
							route: {
								name: 'Site Logs',
								params: {
									name: this.name,
									type: 'pdf'
								}
							}
						},
						{
							title: 'IPython Logs',
							route: {
								name: 'Site Logs',
								params: {
									name: this.name,
									type: 'ipython'
								}
							}
						},
						{
							title: 'Wkhtmltopdf Logs',
							route: {
								name: 'Site Logs',
								params: {
									name: this.name,
									type: 'wkhtmltopdf'
								}
							}
						},
						{
							title: 'Other Logs',
							route: {
								name: 'Site Logs',
								params: {
									name: this.name,
									type: 'other'
								}
							}
						}
					],
					columns: [
						{
							label: 'Title',
							fieldname: 'title',
							width: 0.3
						},
						{
							label: '',
							fieldname: 'action',
							type: 'Button',
							align: 'right',
							Button: ({ row }) => {
								return {
									label: 'View',
									type: 'primary',
									iconRight: 'arrow-right',
									onClick: () => {
										this.$router.push(row.route);
									}
								};
							}
						}
					]
				};
			}
		}
	}
};
</script>
