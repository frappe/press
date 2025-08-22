<template>
	<div class="flex h-full flex-col">
		<div class="sticky top-0 z-10 shrink-0">
			<Header>
				<Breadcrumbs
					:items="[{ label: 'Site Backups', route: '/backups/sites' }]"
				/>
			</Header>
		</div>
		<div class="p-5">
			<ObjectList :options="listOptions" />
		</div>
	</div>
</template>

<script>
import ObjectList from '../../components/ObjectList.vue';
import { bytes, date } from '../../utils/format';

export default {
	name: 'SiteBackups',
	components: {
		ObjectList,
	},
	computed: {
		listOptions() {
			return {
				doctype: 'Site Backup',
				filters: () => {
					return {
						status: ['in', ['Pending', 'Running', 'Success']],
					};
				},
				orderBy: 'creation desc',
				fields: [
					'name',
					'job',
					'status',
					'database_url',
					'public_url',
					'private_url',
					'config_file_url',
					'site',
					'remote_database_file',
					'remote_public_file',
					'remote_private_file',
					'remote_config_file',
					'physical',
				],
				columns: [
					{
						label: 'Site',
						fieldname: 'site',
						width: 1,
					},
					{
						label: 'Status',
						fieldname: 'status',
						width: '150px',
						align: 'center',
						type: 'Badge',
					},
					{
						label: 'Database',
						fieldname: 'database_size',
						width: 0.5,
						format(value) {
							return value ? bytes(value) : '';
						},
					},
					{
						label: 'Public Files',
						fieldname: 'public_size',
						width: 0.5,
						format(value) {
							return value ? bytes(value) : '';
						},
					},
					{
						label: 'Private Files',
						fieldname: 'private_size',
						width: 0.5,
						format(value) {
							return value ? bytes(value) : '';
						},
					},
					{
						label: 'Offsite',
						fieldname: 'offsite',
						width: 0.25,
						type: 'Icon',
						Icon(value) {
							return value ? 'check' : '';
						},
					},
					{
						label: 'Physical',
						fieldname: 'physical',
						width: 0.25,
						type: 'Icon',
						Icon(value) {
							return value ? 'check' : '';
						},
					},

					{
						label: 'Timestamp',
						fieldname: 'creation',
						align: 'right',
						format(value) {
							return `${date(value, 'llll')}`;
						},
					},
				],
				filterControls() {
					return [
						{
							type: 'link',
							label: 'Site',
							fieldname: 'site',
							options: {
								doctype: 'Site',
							},
						},
						{
							type: 'select',
							label: 'Status',
							fieldname: 'status',
							options: ['', 'Success', 'Pending', 'Failure'],
						},
						{
							type: 'date',
							label: 'Backup Date',
							fieldname: 'backup_date',
						},
						{
							type: 'checkbox',
							label: 'Physical',
							fieldname: 'physical',
						},
						{
							type: 'checkbox',
							label: 'Offsite',
							fieldname: 'offsite',
						},
					];
				},
				onRowClick: (record) => {
					this.$router.push({
						name: 'Site Detail Backups',
						params: {
							name: record.site,
						},
						query: {
							name: record.name,
						},
					});
				},
			};
		},
	},
};
</script>
