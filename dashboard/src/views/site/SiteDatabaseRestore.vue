<template>
	<Card
		v-if="site"
		title="Restore, Migrate & Reset"
		:subtitle="
			site.status === 'Suspended'
				? 'Activate the site to enable these actions'
				: ''
		"
	>
		<div class="divide-y">
			<div class="flex items-center justify-between py-3">
				<div>
					<h3 class="text-lg">Restore</h3>
					<p class="mt-1 text-base text-gray-600">
						Restore your database using a previous backup
					</p>
				</div>
				<Tooltip
					:text="
						!permissions.restore
							? `You don't have enough permissions to perform this action`
							: 'Restore Database'
					"
				>
					<Button
						theme="red"
						:disabled="site.status === 'Suspended' || !permissions.restore"
						@click="showRestoreDialog = true"
					>
						Restore
					</Button>
				</Tooltip>
			</div>
			<div class="flex items-center justify-between py-3">
				<div>
					<h3 class="text-lg">Migrate</h3>
					<p class="mt-1 text-base text-gray-600">
						Run bench migrate command on your database
					</p>
				</div>
				<Tooltip
					:text="
						!permissions.migrate
							? `You don't have enough permissions to perform this action`
							: 'Migrate Database'
					"
				>
					<Button
						:disabled="site.status === 'Suspended' || !permissions.migrate"
						@click="showMigrateDialog = true"
					>
						Migrate
					</Button>
				</Tooltip>
			</div>
			<div class="flex items-center justify-between py-3">
				<div>
					<h3 class="text-lg">Reset</h3>
					<p class="mt-1 text-base text-gray-600">
						Reset your database to a clean state
					</p>
				</div>
				<Tooltip
					:text="
						!permissions.reset
							? `You don't have enough permissions to perform this action`
							: 'Reset Database'
					"
				>
					<Button
						theme="red"
						:disabled="site.status === 'Suspended' || !permissions.reset"
						@click="showResetDialog = true"
					>
						Reset
					</Button>
				</Tooltip>
			</div>
			<div class="flex items-center justify-between py-3">
				<div>
					<h3 class="text-lg">Clear Cache</h3>
					<p class="mt-1 text-base text-gray-600">Clear your site's cache</p>
				</div>
				<Button
					:disabled="site.status === 'Suspended'"
					@click="confirmClearCache"
				>
					Clear
				</Button>
			</div>
			<div
				class="flex items-center justify-between py-3"
				v-if="$account.team.database_access_enabled"
			>
				<div>
					<h3 class="text-lg">Access</h3>
					<p class="mt-1 text-base text-gray-600">Connect to your database</p>
				</div>
				<Tooltip
					:text="
						!permissions.access
							? `You don't have enough permissions to perform this action`
							: 'Access Database'
					"
				>
					<Button
						:disabled="!permissions.access"
						icon-left="database"
						@click="showDatabaseAccessDialog = true"
					>
						Access</Button
					>
				</Tooltip>
			</div>
		</div>

		<Dialog
			:options="{
				title: 'Migrate Database',
				actions: [
					{
						label: 'Migrate',
						variant: 'solid',
						theme: 'red',
						loading: $resources.migrateDatabase.loading,
						onClick: migrateDatabase
					}
				]
			}"
			v-model="showMigrateDialog"
			@close="
				() => {
					$resources.migrateDatabase.reset();
					wantToSkipFailingPatches = false;
				}
			"
		>
			<template v-slot:body-content>
				<p class="text-base">
					<b>bench migrate</b> command will be executed on your database. Are
					you sure you want to run this command? We recommend that you download
					a database backup before continuing.
				</p>
				<ErrorMessage
					class="mt-2"
					:message="$resources.migrateDatabase.error"
				/>
				<div class="mt-2">
					<!-- Skip Failing Checkbox -->
					<input
						id="skip-failing"
						type="checkbox"
						class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
						v-model="wantToSkipFailingPatches"
					/>
					<label for="skip-failing" class="ml-2 text-sm text-gray-900">
						Skip failing patches (if any patch fails)
					</label>
				</div>
			</template>
		</Dialog>

		<Dialog
			:options="{
				title: 'Restore',
				actions: [
					{
						label: 'Restore',
						variant: 'solid',
						loading: $resources.restoreBackup.loading,
						onClick: () => $resources.restoreBackup.submit()
					}
				]
			}"
			v-model="showRestoreDialog"
		>
			<template v-slot:body-content>
				<div class="space-y-4">
					<p class="text-base">
						Restore your database using a previous backup.
					</p>
					<BackupFilesUploader v-model:backupFiles="selectedFiles" />
				</div>
				<div class="mt-3">
					<!-- Skip Failing Checkbox -->
					<input
						id="skip-failing"
						type="checkbox"
						class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
						v-model="wantToSkipFailingPatches"
					/>
					<label for="skip-failing" class="ml-2 text-sm text-gray-900">
						Skip failing patches (if any patch fails)
					</label>
				</div>
				<ErrorMessage class="mt-2" :message="$resources.restoreBackup.error" />
			</template>
		</Dialog>

		<DatabaseAccessDialog
			v-if="showDatabaseAccessDialog"
			:site="site.name"
			v-model:show="showDatabaseAccessDialog"
		/>

		<Dialog
			:options="{
				title: 'Reset Database',
				actions: [
					{
						label: 'Reset',
						variant: 'solid',
						theme: 'red',
						loading: $resources.resetDatabase.loading,
						onClick: () => $resources.resetDatabase.submit()
					}
				]
			}"
			v-model="showResetDialog"
		>
			<template v-slot:body-content>
				<p class="text-base">
					All the data from your site will be lost. Are you sure you want to
					reset your database?
				</p>
				<p class="mt-4 text-base">
					Please type
					<span class="font-semibold">{{ site.name }}</span> to confirm.
				</p>
				<FormControl class="mt-4 w-full" v-model="confirmSiteName" />
				<ErrorMessage class="mt-2" :message="$resources.resetDatabase.error" />
			</template>
		</Dialog>
	</Card>
</template>

<script>
import FileUploader from '@/components/FileUploader.vue';
import BackupFilesUploader from '@/components/BackupFilesUploader.vue';
import DatabaseAccessDialog from './DatabaseAccessDialog.vue';

export default {
	name: 'SiteDatabase',
	components: {
		FileUploader,
		BackupFilesUploader,
		DatabaseAccessDialog
	},
	props: ['site'],
	data() {
		return {
			confirmSiteName: '',
			showResetDialog: false,
			showMigrateDialog: false,
			showRestoreDialog: false,
			showDatabaseAccessDialog: false,
			selectedFiles: {
				database: null,
				public: null,
				private: null
			},
			wantToSkipFailingPatches: false
		};
	},
	resources: {
		restoreBackup() {
			return {
				url: 'press.api.site.restore',
				params: {
					name: this.site?.name,
					files: this.selectedFiles,
					skip_failing_patches: this.wantToSkipFailingPatches
				},
				validate() {
					if (!this.filesUploaded) {
						return 'Please upload database, public and private files to restore.';
					}
				},
				onSuccess(jobName) {
					this.selectedFiles = {};
					this.$router.push({ name: 'SiteJobs', params: { jobName } });
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			};
		},
		resetDatabase() {
			return {
				url: 'press.api.site.reinstall',
				params: {
					name: this.site?.name
				},
				validate() {
					if (this.confirmSiteName !== this.site?.name) {
						return 'Please type the site name to confirm.';
					}
				},
				onSuccess(jobName) {
					this.$router.push({ name: 'SiteJobs', params: { jobName } });
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			};
		},
		migrateDatabase() {
			return {
				url: 'press.api.site.migrate',
				params: {
					name: this.site?.name
				},
				onSuccess() {
					this.$router.push({
						name: 'SiteOverview',
						params: { site: this.site?.name }
					});
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			};
		},
		clearCache() {
			return {
				url: 'press.api.site.clear_cache',
				params: {
					name: this.site?.name
				},
				onSuccess() {
					this.$router.push({
						name: 'SiteOverview',
						params: { site: this.site?.name }
					});
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			};
		}
	},
	methods: {
		migrateDatabase() {
			this.$resources.migrateDatabase.submit({
				name: this.site.name,
				skip_failing_patches: this.wantToSkipFailingPatches
			});
		},
		confirmClearCache() {
			this.$confirm({
				title: 'Clear Cache',
				message: `
					<b>bench clear-cache</b> and <b>bench clear-website-cache</b> commands will be executed on your site. Are you sure
					you want to run these command?
				`,
				actionLabel: 'Clear Cache',
				actionColor: 'red',
				action: closeDialog => {
					this.$resources.clearCache.submit();
					closeDialog();
				}
			});
		}
	},
	computed: {
		permissions() {
			return {
				migrate: this.$account.hasPermission(
					this.site.name,
					'press.api.site.migrate'
				),
				restore: this.$account.hasPermission(
					this.site.name,
					'press.api.site.restore'
				),
				reset: this.$account.hasPermission(
					this.site.name,
					'press.api.site.reset'
				),
				access: this.$account.hasPermission(
					this.site.name,
					'press.api.site.enable_database_access'
				)
			};
		},
		filesUploaded() {
			return this.selectedFiles.database;
		}
	}
};
</script>
