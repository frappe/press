<template>
	<Card
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
				<Button
					:disabled="site.status === 'Suspended'"
					@click="showRestoreDialog = true"
				>
					Restore Database
				</Button>
			</div>
			<div class="flex items-center justify-between py-3">
				<div>
					<h3 class="text-lg">Migrate</h3>
					<p class="mt-1 text-base text-gray-600">
						Run bench migrate command on your database.
					</p>
				</div>
				<Button
					:disabled="site.status === 'Suspended'"
					@click="showMigrateDialog = true"
				>
					Migrate Database
				</Button>
			</div>
			<div class="flex items-center justify-between py-3">
				<div>
					<h3 class="text-lg">Reset</h3>
					<p class="mt-1 text-base text-gray-600">
						Reset your database to a clean state.
					</p>
				</div>
				<Button :disabled="site.status === 'Suspended'" @click="confirmReset">
					<span class="text-red-600">
						Reset Database
					</span>
				</Button>
			</div>
			<div class="flex items-center justify-between py-3">
				<div>
					<h3 class="text-lg">Clear Cache</h3>
					<p class="mt-1 text-base text-gray-600">
						Clear your site's cache.
					</p>
				</div>
				<Button
					:disabled="site.status === 'Suspended'"
					@click="confirmClearCache"
				>
					<span class="text-red-600">
						Clear Cache
					</span>
				</Button>
			</div>
		</div>

		<Dialog
			title="Migrate Database"
			v-model="showMigrateDialog"
			:dismissable="true"
			@close="
				() => {
					$resources.migrateDatabase.reset();
					wantToSkipFailingPatches = false;
				}
			"
		>
			<p class="text-base">
				<b>bench migrate</b> command will be executed on your database. Are you
				sure you want to run this command? We recommend that you download a
				database backup before continuing.
			</p>
			<ErrorMessage class="mt-2" :error="$resources.migrateDatabase.error" />
			<div class="mt-2">
				<!-- Skip Failing Checkbox -->
				<input
					id="skip-failing"
					type="checkbox"
					class="
				h-4
				w-4
				text-blue-600
				focus:ring-blue-500
				border-gray-300
				rounded
			"
					v-model="wantToSkipFailingPatches"
				/>
				<label for="skip-failing" class="ml-2 text-sm text-gray-900">
					Skip failing patches (if any patch fails)
				</label>
			</div>
			<template #actions>
				<Button
					type="danger"
					:loading="$resources.migrateDatabase.loading"
					@click="migrateDatabase"
				>
					Migrate
				</Button>
			</template>
		</Dialog>

		<Dialog title="Restore" v-model="showRestoreDialog">
			<div class="space-y-4">
				<p class="text-base">Restore your database using a previous backup.</p>
				<BackupFilesUploader :backupFiles.sync="selectedFiles" />
			</div>
			<div class="mt-3">
				<!-- Skip Failing Checkbox -->
				<input
					id="skip-failing"
					type="checkbox"
					class="
				h-4
				w-4
				text-blue-600
				focus:ring-blue-500
				border-gray-300
				rounded
			"
					v-model="wantToSkipFailingPatches"
				/>
				<label for="skip-failing" class="ml-2 text-sm text-gray-900">
					Skip failing patches (if any patch fails)
				</label>
			</div>
			<ErrorMessage class="mt-2" :error="$resources.restoreBackup.error" />
			<template #actions>
				<Button
					type="primary"
					:loading="$resources.restoreBackup.loading"
					@click="$resources.restoreBackup.submit()"
				>
					Restore Database
				</Button>
			</template>
		</Dialog>
	</Card>
</template>

<script>
import FileUploader from '@/components/FileUploader.vue';
import BackupFilesUploader from '@/components/BackupFilesUploader.vue';

export default {
	name: 'SiteDatabase',
	components: {
		FileUploader,
		BackupFilesUploader
	},
	props: ['site'],
	data() {
		return {
			showMigrateDialog: false,
			showRestoreDialog: false,
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
				method: 'press.api.site.restore',
				params: {
					name: this.site.name,
					files: this.selectedFiles,
					skip_failing_patches: this.wantToSkipFailingPatches
				},
				validate() {
					if (!this.filesUploaded) {
						return 'Please upload database, public and private files to restore.';
					}
				},
				onSuccess() {
					this.selectedFiles = {};
					this.$router.push(`/sites/${this.site.name}/installing`);
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			};
		},
		resetDatabase() {
			return {
				method: 'press.api.site.reinstall',
				params: {
					name: this.site.name
				},
				onSuccess() {
					this.$router.push(`/sites/${this.site.name}/installing`);
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			};
		},
		migrateDatabase() {
			return {
				method: 'press.api.site.migrate',
				params: {
					name: this.site.name
				},
				onSuccess() {
					this.$router.push({
						name: 'SiteOverview',
						params: { site: this.site.name }
					});
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			};
		},
		clearCache() {
			return {
				method: 'press.api.site.clear_cache',
				params: {
					name: this.site.name
				},
				onSuccess() {
					this.$router.push({
						name: 'SiteOverview',
						params: { site: this.site.name }
					});
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			};
		}
	},
	methods: {
		confirmReset() {
			this.$confirm({
				title: 'Reset Database',
				message:
					'All the data from your site will be lost. Are you sure you want to reset your database?',
				actionLabel: 'Reset',
				actionType: 'danger',
				action: closeDialog => {
					this.$resources.resetDatabase.submit();
					closeDialog();
				}
			});
		},
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
				actionType: 'danger',
				action: closeDialog => {
					this.$resources.clearCache.submit();
					closeDialog();
				}
			});
		}
	},
	computed: {
		filesUploaded() {
			return (
				this.selectedFiles.database &&
				this.selectedFiles.public &&
				this.selectedFiles.private
			);
		}
	}
};
</script>
