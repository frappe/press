<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Drop Site',
			actions: [
				{
					label: 'Drop Site',
					variant: 'solid',
					theme: 'red',
					onClick: handleConfirm,
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<p class="text-p-base text-gray-800">
					Are you sure you want to drop your site
					<b>{{ site.doc?.host_name || site.doc?.name }}</b>
					? The site will be archived and all of its files and Offsite Backups
					will be deleted. This action cannot be undone.
				</p>
				<div
					class="flex items-center rounded border border-red-200 bg-red-100 p-4 text-sm text-red-600"
				>
					<lucide-alert-triangle class="mr-4 inline-block h-6 w-6" />
					<div>
						<strong>Warning:</strong> This action will permanently delete all
						site data including files, databases, and backups. This cannot be
						undone.
					</div>
				</div>
				<div class="space-y-4 flex flex-col">
					<FormControl
						type="text"
						label="Please type the site name to confirm"
						placeholder="Site name"
						v-model="confirmSiteName"
						required
					/>
					<FormControl
						type="checkbox"
						label="Take backup before dropping site"
						v-model="createOffsiteBackup"
					/>
					<FormControl
						type="checkbox"
						label="Force drop site"
						v-model="forceDrop"
						description="Force drop the site even if there are pending operations"
					/>
				</div>
				<div
					v-if="createOffsiteBackup"
					class="space-y-2 flex items-center rounded text-sm border border-blue-200 p-2 bg-blue-100 text-blue-700"
				>
					<lucide-info class="mr-3 inline-block h-5 w-5" />
					<div>
						An offsite backup of your site will be stored before site drop. this
						is automatically deleted after 90 days.
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { createResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { useRouter } from 'vue-router';
import { DocumentResource } from '../../objects/common/types';
import { getToastErrorMessage } from '../../utils/toast';
import { PropType, ref } from 'vue';

const props = defineProps({
	site: {
		type: Object as PropType<DocumentResource>,
		required: true,
	},
});

const router = useRouter();

const showDialog = defineModel<boolean>({ default: true });
const createOffsiteBackup = ref(true);
const confirmSiteName = ref('');
const forceDrop = ref(false);

const archiveSite = createResource({
	url: 'press.api.client.run_doc_method',
	makeParams: () => ({
		dt: 'Site',
		dn: props.site.doc?.name,
		method: 'archive',
		args: {
			force: forceDrop.value,
			create_offsite_backup: createOffsiteBackup.value,
		},
	}),
});

const handleConfirm = () => {
	if (archiveSite.loading) return;

	if (
		![props.site.doc?.name, props.site.doc?.host_name].includes(
			confirmSiteName.value,
		)
	) {
		throw new Error('Site name does not match.');
	}

	const loadingMessage = createOffsiteBackup.value
		? 'Creating backup and scheduling site drop...'
		: 'Scheduling site drop...';

	toast.promise(archiveSite.submit(), {
		loading: loadingMessage,
		success: () => {
			showDialog.value = false;
			router.replace({ name: 'Site List' });
			return 'Site drop scheduled successfully';
		},
		error: (e: Error) => getToastErrorMessage(e),
	});
};
</script>
