<template>
	<div class="flex items-center justify-between gap-1">
		<div>
			<h3 class="text-base font-medium">{{ props.actionLabel }}</h3>
			<p class="mt-1 text-p-base text-gray-600">{{ props.description }}</p>
		</div>
		<Button
			v-if="releaseGroup?.doc"
			class="whitespace-nowrap"
			@click="getBenchActionHandler(props.actionLabel)"
		>
			<p
				:class="
					group === 'Dangerous Actions' ? 'text-red-600' : 'text-gray-800'
				"
			>
				{{ props.buttonLabel }}
			</p>
		</Button>
	</div>
</template>

<script setup>
import { getCachedDocumentResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { confirmDialog } from '../../utils/components';
import router from '../../router';

const props = defineProps({
	benchName: { type: String, required: true },
	actionLabel: { type: String, required: true },
	method: { type: String, required: true },
	description: { type: String, required: true },
	buttonLabel: { type: String, required: true },
	group: { type: String, required: false }
});

const releaseGroup = getCachedDocumentResource(
	'Release Group',
	props.benchName
);

function getBenchActionHandler(action) {
	const actionHandlers = {
		'Rename Bench': onRenameBench,
		'Transfer Bench': onTransferBench,
		'Drop Bench': onDropBench
	};
	if (actionHandlers[action]) {
		actionHandlers[action].call(this);
	}
}

function onRenameBench() {
	confirmDialog({
		title: 'Rename Bench',
		fields: [
			{
				label: 'Enter new bench name',
				fieldname: 'newBenchName'
			}
		],
		onSuccess({ hide, values }) {
			if (values.newBenchName) {
				toast.promise(
					releaseGroup.setValue.submit(
						{
							title: values.newBenchName
						},
						{
							onSuccess() {
								hide();
							}
						}
					),
					{
						loading: 'Renaming bench...',
						success: 'Bench renamed successfully',
						error: 'Failed to rename bench'
					}
				);
			} else {
				toast.error('Please enter a valid bench name');
			}
		}
	});
}

function onTransferBench() {
	confirmDialog({
		title: 'Transfer Bench Ownership',
		fields: [
			{
				label:
					'Enter email address of the team for transfer of bench ownership',
				fieldname: 'email'
			},
			{
				label: 'Reason for transfer',
				fieldname: 'reason',
				type: 'textarea'
			}
		],
		primaryAction: {
			label: 'Transfer',
			variant: 'solid',
			onClick: ({ hide, values }) => {
				if (!values.email) {
					throw new Error('Please enter a valid email address');
				}

				return releaseGroup.sendTransferRequest
					.submit({ team_mail_id: values.email, reason: values.reason || '' })
					.then(() => {
						hide();
						toast.success(
							`Transfer request sent to ${values.email} successfully.`
						);
					});
			}
		}
	});
}

function onDropBench() {
	confirmDialog({
		title: 'Drop Bench',
		message: `Are you sure you want to drop the bench <b>${
			releaseGroup.doc.title || releaseGroup.name
		}</b>?`,
		fields: [
			{
				label: 'Please type the bench name to confirm',
				fieldname: 'confirmBenchName'
			}
		],
		primaryAction: {
			label: 'Drop',
			theme: 'red',
			onClick: ({ hide, values }) => {
				if (releaseGroup.archive.loading) return;
				if (values.confirmBenchName !== releaseGroup.doc.title) {
					throw new Error('Bench name does not match');
				}
				toast.promise(
					releaseGroup.archive.submit(null, {
						onSuccess: () => {
							hide();
							router.push({ name: 'Release Group List' });
						}
					}),
					{
						loading: 'Dropping bench...',
						success: 'Bench dropped successfully',
						error: error =>
							error.messages.length
								? error.messages.join('\n')
								: 'Failed to drop bench'
					}
				);
			}
		}
	});
}
</script>
