<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Restore Backup on Another Site',
			actions: [
				{
					label: 'Restore',
					variant: 'solid',
					theme: 'red',
					disabled:
						!selectedSite ||
						(!restoreDatabase &&
							!restorePublic &&
							!restorePrivate &&
							!restoreConfig),
					onClick: restore,
				},
			],
		}"
	>
		<template #body-content>
			<FormControl
				label="Select the site where you want to restore the backup"
				class="mt-4"
				type="combobox"
				:modelValue="selectedSite?.value"
				@update:modelValue="
					selectedSite = ($resources.sites.data || [])
						.map((site) => {
							return {
								label: site.host_name || site.name,
								value: site.name,
							};
						})
						.find((option) => option.value === $event)
				"
				:options="
					($resources.sites.data || []).map((site) => {
						return {
							label: site.host_name || site.name,
							value: site.name,
						};
					})
				"
			/>
			<AlertBanner
				v-if="selectedSite"
				class="mt-4"
				type="warning"
				:title="`Restoring will overwrite the current data of <strong>${selectedSite.value}</strong> with the backup data of <strong>${site}</strong>`"
			/>

			<div v-if="selectedSite" class="mt-4">
				<p class="text text-base text-gray-800 font-semibold mb-4">
					Please select the data you want to restore :
				</p>
				<div class="flex flex-col gap-2">
					<FormControl
						type="checkbox"
						size="sm"
						variant="subtle"
						label="Database"
						v-if="database_backup_exists"
						v-model="restoreDatabase"
					/>
					<FormControl
						type="checkbox"
						size="sm"
						variant="subtle"
						label="Public Files"
						v-if="public_backup_exists"
						v-model="restorePublic"
					/>
					<FormControl
						type="checkbox"
						size="sm"
						variant="subtle"
						label="Private Files"
						v-if="private_backup_exists"
						v-model="restorePrivate"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
import AlertBanner from '../AlertBanner.vue';

export default {
	name: 'SelectSiteForRestore',
	props: [
		'site',
		'database_backup_exists',
		'public_backup_exists',
		'private_backup_exists',
		'config_backup_exists',
	],
	emits: ['restore'],
	data() {
		return {
			selectedSite: null,
			showDialog: true,
			restoreDatabase: this.database_backup_exists,
			restorePublic: this.public_backup_exists,
			restorePrivate: this.private_backup_exists,
		};
	},
	components: {
		AlertBanner,
	},
	resources: {
		sites() {
			return {
				type: 'list',
				doctype: 'Site',
				fields: ['host_name', 'name'],
				filters: { name: ['!=', this.site] },
				pageLength: 500,
				auto: true,
			};
		},
	},
	methods: {
		restore() {
			this.$emit('restore', {
				selectedSite: this.selectedSite.value,
				restoreDatabase: this.restoreDatabase,
				restorePublic: this.restorePublic,
				restorePrivate: this.restorePrivate,
				restoreConfig: this.restoreDatabase, // Always restore config if database is restored
			});
			this.showDialog = false;
		},
	},
};
</script>
