<template>
	<ObjectList class="p-5" :options="logsOptions" />
</template>

<script>
import { date } from '../../utils/format';
import ObjectList from '../ObjectList.vue';

export default {
	name: 'SiteLogs',
	props: ['name'],
	components: {
		ObjectList
	},
	computed: {
		logsOptions() {
			return {
				resource: () => {
					return {
						url: 'press.api.site.logs',
						params: {
							name: this.name
						},
						auto: true,
						cache: ['ObjectList', 'press.api.site.logs', this.name]
					};
				},
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
					}
				]
			};
		}
	}
};
</script>
