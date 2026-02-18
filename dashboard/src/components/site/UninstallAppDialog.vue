<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: `Uninstall ${app.title || app.app_title}`,
			actions: [
				{
					label: 'Uninstall',
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
					Are you sure you want to uninstall the
					<b>{{ app.title || app.app_title }}</b> app from the site
					<b>{{ site.doc?.host_name || site.doc?.name }}</b>
					?
				</p>
				<AlertBanner
					title="All <b>doctypes</b> & <b>modules</b>, along with all the
						<b>data</b> within this app will be removed from the site."
					type="warning"
				>
				</AlertBanner>
				<div class="">
					<FormControl
						type="checkbox"
						label="Create an offsite backup"
						v-model="createOffsiteBackup"
					/>
					<span class="block text-xs text-ink-gray-5 ml-[1.4rem]"
						>An offsite backup of your site will be taken before uninstalling
						app</span
					>
				</div>
				<div v-if="app.collect_feedback" class="space-y-4">
					<FormControl
						type="checkbox"
						label="Give feedback"
						v-model="giveFeedback"
					/>
					<FormControl
						v-if="giveFeedback"
						type="select"
						label="Feedback"
						v-model="feedback"
						:options="feedbackOptions"
					/>
					<FormControl
						v-if="giveFeedback && feedback === 'Other'"
						type="textarea"
						label="Specify feedback"
						v-model="specifyFeedback"
					/>
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
import AlertBanner from '../AlertBanner.vue';

const props = defineProps({
	site: {
		type: Object as PropType<DocumentResource>,
		required: true,
	},
	app: {
		type: Object,
		required: true,
	},
});

const router = useRouter();

const showDialog = defineModel<boolean>({ default: true });
const giveFeedback = ref(false);
const feedback = ref('');
const specifyFeedback = ref('');
const createOffsiteBackup = ref(true);
const feedbackOptions = [
	'Switched to another tool',
	'Was just testing, not a long-term user',
	'Missing features I needed',
	'Setup and onboarding were too complex',
	'Prefer self-hosting over Frappe Cloud',
	'Too expensive for my use case',
	'Other',
].map((option) => ({ label: option, value: option }));

const uninstallApp = createResource({
	url: 'press.api.client.run_doc_method',
	makeParams: () => ({
		dt: 'Site',
		dn: props.site.doc?.name,
		method: 'uninstall_app',
		args: {
			app: props.app.app,
			create_offsite_backup: createOffsiteBackup.value,
			feedback:
				feedback.value === 'Other' ? specifyFeedback.value : feedback.value,
		},
	}),
});

const handleConfirm = () => {
	if (uninstallApp.loading) return;

	toast.promise(uninstallApp.submit(), {
		loading: 'Scheduling app uninstall...',
		success: (jobId: { message: string }) => {
			showDialog.value = false;
			router.push({
				name: 'Site Job',
				params: {
					name: props.site.name,
					id: jobId.message,
				},
			});
			return 'App uninstall scheduled';
		},
		error: (e: Error) => getToastErrorMessage(e),
	});
};
</script>
