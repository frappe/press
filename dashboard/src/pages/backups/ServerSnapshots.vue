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
import { date } from '../../utils/format';

export default {
	name: 'Server Snapshots',
	components: {
		ObjectList,
	},
	computed: {
		listOptions() {
			return {
				doctype: 'Server Snapshot',
				filters: () => {
					return { status: ['!=', 'Unavailable'] };
				},
				orderBy: 'creation desc',
				fields: [
					'name',
					'status',
					'creation',
					'consistent',
					'free',
					'expire_at',
					'total_size_gb',
					'app_server',
					'database_server',
				],
				columns: [
					{
						label: 'Snapshot',
						fieldname: 'name',
						width: 0.5,
						class: 'font-medium',
					},
					{
						label: 'Status',
						fieldname: 'status',
						type: 'Badge',
						width: 0.5,
						align: 'center',
					},
					{
						label: 'App Server',
						fieldname: 'app_server',
						width: 1,
					},
					{
						label: 'Database Server',
						fieldname: 'database_server',
						width: 1,
					},
					{
						label: 'Size',
						fieldname: 'total_size_gb',
						width: 0.5,
						align: 'center',
						format(value) {
							if (!value) return '-';
							return `${value} GB`;
						},
					},
					{
						label: 'Consistent',
						fieldname: 'consistent',
						width: 0.3,
						type: 'Icon',
						align: 'center',
						Icon(value) {
							return value ? 'check' : 'x';
						},
					},
					{
						label: 'Free',
						fieldname: 'free',
						width: 0.3,
						type: 'Icon',
						Icon(value) {
							return value ? 'check' : 'x';
						},
					},
					{
						label: 'Locked',
						fieldname: 'locked',
						width: 0.3,
						type: 'Icon',
						align: 'center',
						Icon(value) {
							return value ? 'lock' : 'unlock';
						},
					},
					{
						label: 'Expire At',
						fieldname: 'expire_at',
						width: 0.5,
						align: 'center',
						format(value) {
							if (!value) return 'No Expiry';
							return date(value, 'llll');
						},
					},
					{
						label: 'Timestamp',
						fieldname: 'creation',
						align: 'right',
						format(value) {
							return date(value, 'llll');
						},
					},
				],
				filterControls() {
					return [
						{
							type: 'link',
							label: 'App Server',
							fieldname: 'app_server',
							options: {
								doctype: 'Server',
							},
						},
						{
							type: 'link',
							label: 'Database Server',
							fieldname: 'database_server',
							options: {
								doctype: 'Database Server',
							},
						},
						{
							type: 'select',
							label: 'Status',
							fieldname: 'status',
							options: [
								'',
								'Pending',
								'Processing',
								'Failure',
								'Completed',
								'Unavailable',
							],
						},
						{
							type: 'date',
							label: 'Backup Date',
							fieldname: 'backup_date',
						},
						{
							type: 'checkbox',
							label: 'Consistent',
							fieldname: 'consistent',
						},
					];
				},
				onRowClick: (record) => {
					this.$router.push({
						name: 'Server Detail Snapshots',
						params: {
							name: record.app_server,
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
