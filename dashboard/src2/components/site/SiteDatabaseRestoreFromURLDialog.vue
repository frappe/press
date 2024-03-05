<template>
	<Dialog
		:options="{
			title: 'Restore from an existing site',
			actions: [
				{
					label: 'Restore',
					variant: 'solid',
					loading: $resources.restoreBackup.loading,
					disabled: !$resources.getBackupLinks.data,
					onClick: () => $resources.restoreBackup.submit()
				}
			]
		}"
		v-model="showRestoreDialog"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl label="Site URL" v-model="siteURL" />
				<FormControl label="Email" v-model="email" />
				<FormControl label="Password" type="password" v-model="password" />
				<div class="flex text-base" v-if="$resources.getBackupLinks.data">
					<GreenCheckIcon class="mr-2 w-4" />
					Found latest backups from {{ fetchedBackupFileTimestamp }}
				</div>
				<Button
					v-else
					@click="$resources.getBackupLinks.submit()"
					:loading="$resources.getBackupLinks.loading"
				>
					Get Backups
				</Button>
			</div>
			<div class="mt-3">
				<FormControl
					label="Skip failing patches (if any patch fails)"
					type="checkbox"
					v-model="skipFailingPatches"
				/>
			</div>
			<ErrorMessage
				class="mt-2"
				:message="
					$resources.restoreBackup.error || $resources.getBackupLinks.error
				"
			/>
		</template>
	</Dialog>
</template>
<script>
import { date } from '../../utils/format';

export default {
	name: 'SiteDatabaseRestoreDialog',
	props: {
		site: {
			type: String,
			required: true
		}
	},
	data() {
		return {
			siteURL: '',
			email: '',
			password: '',
			selectedFiles: {
				database: null,
				public: null,
				private: null
			},
			showRestoreDialog: true,
			skipFailingPatches: false
		};
	},
	resources: {
		getBackupLinks() {
			return {
				url: 'press.api.site.get_backup_links',
				params: {
					url: this.siteURL,
					email: this.email,
					password: this.password
				},
				validate() {
					if (!this.siteURL) {
						return 'Site URL is required';
					}
					if (!this.email) {
						return 'Email is required';
					}
					if (!this.password) {
						return 'Password is required';
					}
				},
				onSuccess(remoteFiles) {
					for (let file of remoteFiles) {
						this.selectedFiles[file.type] = file.remote_file;
					}
				}
			};
		},
		restoreBackup() {
			return {
				url: 'press.api.site.restore',
				params: {
					name: this.site,
					files: this.selectedFiles,
					skip_failing_patches: this.skipFailingPatches
				},
				validate() {
					if (!this.selectedFiles.database) {
						return 'Something went wrong while fetching the backups from the site';
					}
				},
				onSuccess() {
					this.siteURL = '';
					this.email = '';
					this.password = '';

					this.$router.push({
						name: 'Site Detail Jobs',
						params: { objectType: 'Site', name: this.site }
					});
				}
			};
		}
	},
	computed: {
		fetchedBackupFileTimestamp() {
			if (!this.$resources.getBackupLinks.data) return '';

			let backup = this.$resources.getBackupLinks.data[0];
			let timestamp_string = backup.file_name
				.split('-')[0]
				.split('_')
				.join('T');

			return date(timestamp_string);
		}
	}
};
</script>
