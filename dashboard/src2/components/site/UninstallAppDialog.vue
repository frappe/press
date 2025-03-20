<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: `Uninstall ${app.title}`,
			actions: [
				{
					label: 'Uninstall',
					variant: 'solid',
					onClick: handleConfirm,
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<p class="text-p-base text-gray-800">
					Are you sure you want to uninstall the app
					<b>{{ app.title }}</b> from the site
					<b>{{ site.doc?.host_name || site.doc?.name }}</b>
					?
					<br />
					All doctypes and modules related to this app will be removed.
				</p>
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
