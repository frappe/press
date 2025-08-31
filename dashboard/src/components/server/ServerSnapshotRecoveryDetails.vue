<template>
	<div
		class="flex h-60 w-full items-center justify-center gap-2 text-base text-gray-700"
		v-if="$resources?.snapshotRecovery?.loading"
	>
		<Spinner class="w-4" /> Loading ...
	</div>
	<div>
		<ObjectList :options="siteOptions" />
	</div>
</template>

<script>
import { Spinner } from 'frappe-ui';
import ObjectList from '../ObjectList.vue';
export default {
	name: 'ServerSnapshotRecoveryDetails',
	props: {
		name: {
			type: String,
			required: true,
		},
	},
	components: {
		Spinner,
		ObjectList,
	},
	data() {
		return {};
	},
	resources: {
		snapshotRecovery() {
			return {
				type: 'document',
				doctype: 'Server Snapshot Recovery',
				name: this.name,
				auto: true,
				whitelistedMethods: {
					downloadBackup: 'download_backup',
				},
			};
		},
	},
	computed: {
		sites() {
			return this.$resources?.snapshotRecovery?.doc?.sites_data || [];
		},
		siteOptions() {
			return {
				data: () => this.sites,
				columns: [
					{
						label: 'Site',
						fieldname: 'site',
						width: 0.5,
						type: 'Text',
						align: 'left',
						format(value) {
							if (value.length > 15) {
								return value.substring(0, 15) + '...';
							}
							return value;
						},
					},
					{
						label: 'Status',
						fieldname: 'status',
						width: 0.3,
						type: 'Badge',
						align: 'center',
					},
					{
						label: 'Database',
						fieldname: 'database_backup_available',
						width: 0.3,
						type: 'Icon',
						align: 'center',
						Icon(value) {
							return value ? 'check' : 'x';
						},
					},
					{
						label: 'Public Files',
						fieldname: 'public_files_backup_available',
						width: 0.3,
						type: 'Icon',
						align: 'center',
						Icon(value) {
							return value ? 'check' : 'x';
						},
					},
					{
						label: 'Private Files',
						fieldname: 'private_files_backup_available',
						width: 0.3,
						type: 'Icon',
						align: 'center',
						Icon(value) {
							return value ? 'check' : 'x';
						},
					},
				],
				rowActions: ({ row }) => {
					if (row.status !== 'Success') {
						return [];
					}
					return [
						{
							group: 'Download',
							items: [
								{
									label: 'Download Database',
									onClick: () => {
										return this.download(row, 'database');
									},
									condition: () => row.database_backup_available,
								},
								{
									label: 'Download Public Files',
									onClick: () => {
										return this.download(row, 'public');
									},
									condition: () => row.public_files_backup_available,
								},
								{
									label: 'Download Private Files',
									onClick: () => {
										return this.download(row, 'private');
									},
									condition: () => row.private_files_backup_available,
								},
								{
									label: 'Download Encryption Key',
									onClick: () => {
										return this.download(row, 'encryption_key');
									},
									condition: () => row.encryption_key_available,
								},
							],
						},
					];
				},
			};
		},
	},
	methods: {
		download(row, type) {
			this.$resources.snapshotRecovery.downloadBackup.submit(
				{ site: row.site, file_type: type },
				{
					onSuccess(r) {
						const data = r.message;
						if (!data) {
							return;
						}
						if (type === 'encryption_key') {
							// Create a file
							const blob = new Blob([data], { type: 'text/plain' });
							const url = window.URL.createObjectURL(blob);
							const a = document.createElement('a');
							a.href = url;
							a.download = `${row.site}_${type}.txt`;
							document.body.appendChild(a);
							a.click();
							document.body.removeChild(a);
							window.URL.revokeObjectURL(url);
						} else {
							window.open(r.message);
						}
					},
				},
			);
		},
	},
};
</script>
