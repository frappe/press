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
				<AlertBanner
					:title="`Site <b>${site.doc?.host_name || site.doc?.name}</b> will be archived. All files and backups will be permanently deleted.`"
					type="warning"
				>
				</AlertBanner>
				<div class="space-y-4 flex flex-col">
					<FormControl
						type="text"
						label="Please type the site name to confirm"
						placeholder="Site name"
						v-model="confirmSiteName"
						required
					/>
					<div>
						<FormControl
							type="checkbox"
							label="Create offsite backup before site drop"
							v-model="createOffsiteBackup"
						/>
						<span class="block text-xs text-ink-gray-5 ml-[1.4rem]"
							>Recoverable up to 6 months</span
						>
					</div>
					<div>
						<FormControl
							type="checkbox"
							label="Force drop site"
							v-model="forceDrop"
						/>
						<span class="block text-xs text-ink-gray-5 ml-[1.4rem]"
							>Drop the site even if there are pending operations</span
						>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { createResource } from 'frappe-ui';
import AlertBanner from '../AlertBanner.vue';
import { toast } from 'vue-sonner';
import { useRouter } from 'vue-router';
import { DocumentResource } from '../../objects/common/types';
import { getToastErrorMessage } from '../../utils/toast';
import { PropType, ref, defineAsyncComponent, h } from 'vue';
import { isLastSite } from '../../data/team';
import { renderDialog } from '../../utils/components';

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

const handleConfirm = async () => {
	if (archiveSite.loading) return;
	if (
		![props.site.doc?.name, props.site.doc?.host_name].includes(
			confirmSiteName.value,
		)
	) {
		toast.error('Site name does not match.');
		return;
	}

	try {
		await archiveSite.submit();
		toast.success('Site drop scheduled successfully');
		showDialog.value = false;

		const isLast = await isLastSite(props.site.doc?.team);
		if (isLast) {
			const ChurnFeedbackDialog = defineAsyncComponent(
				() => import('../ChurnFeedbackDialog.vue'),
			);
			renderDialog(
				h(ChurnFeedbackDialog, {
					team: props.site.doc?.team,
					onUpdated() {
						router.replace({ name: 'Site List' });
					},
				}),
			);
		} else {
			router.replace({ name: 'Site List' });
		}
	} catch (e: any) {
		const errorMsg = getToastErrorMessage(e);
		toast.error(errorMsg);
	}
};
</script>
