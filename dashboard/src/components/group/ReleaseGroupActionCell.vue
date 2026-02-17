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
	group: { type: String, required: false },
	linkedVersionUpgrade: { type: Boolean, required: false, default: false },
});

const releaseGroup = getCachedDocumentResource(
	'Release Group',
	props.benchName,
);

function getBenchActionHandler(action) {
	const actionHandlers = {
		'Rename Bench Group': onRenameBench,
		'Transfer Bench Group': onTransferBench,
		'Drop Bench Group': onDropBench,
	};
	if (actionHandlers[action]) {
		actionHandlers[action].call(this);
	}
}

function onRenameBench() {
	confirmDialog({
		title: 'Rename Bench Group',
		fields: [
			{
				label: 'Enter new bench group name',
				fieldname: 'newBenchName',
			},
		],
		onSuccess({ hide, values }) {
			if (values.newBenchName) {
				toast.promise(
					releaseGroup.setValue.submit(
						{
							title: values.newBenchName,
						},
						{
							onSuccess() {
								hide();
							},
						},
					),
					{
						loading: 'Renaming bench group...',
						success: 'Bench group renamed successfully',
						error: 'Failed to rename bench group',
					},
				);
			} else {
				toast.error('Please enter a valid bench group name');
			}
		},
	});
}

function onTransferBench() {
	confirmDialog({
		title: 'Transfer Bench Group Ownership',
		fields: [
			{
				label:
					'Enter email address of the team for transfer of bench group ownership',
				fieldname: 'email',
			},
			{
				label: 'Reason for transfer',
				fieldname: 'reason',
				type: 'textarea',
			},
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
							`Transfer request sent to ${values.email} successfully.`,
						);
					});
			},
		},
	});
}

function onDropBench() {
	let message = `Are you sure you want to drop the bench group <b>${
		releaseGroup.doc.title || releaseGroup.name
	}</b>?`;

	if (props.linkedVersionUpgrade) {
		message = `
			<div class="mb-4 p-3 bg-yellow-50 border-l-4 border-yellow-400 text-yellow-800">
				<p class="font-semibold">Warning</p>
				<p class="mt-1">This bench group was created for upgrading your site's version and dropping this will cancel the site upgrade as well.</p>
			</div>
			${message}
		`;
	}

	confirmDialog({
		title: 'Drop Bench Group',
		message: message,
		fields: [
			{
				label: 'Please type the bench group name to confirm',
				fieldname: 'confirmBenchName',
			},
		],
		primaryAction: {
			label: 'Drop',
			theme: 'red',
			onClick: ({ hide, values }) => {
				if (releaseGroup.delete.loading) return;
				if (values.confirmBenchName !== releaseGroup.doc.title) {
					throw new Error('Bench group name does not match');
				}
				toast.promise(
					releaseGroup.delete.submit(null, {
						onSuccess: () => {
							hide();
							router.push({ name: 'Release Group List' });
						},
					}),
					{
						loading: 'Dropping bench group...',
						success: 'Bench group dropped successfully',
						error: (error) =>
							error.messages.length
								? error.messages.join('\n')
								: 'Failed to drop bench group',
					},
				);
			},
		},
	});
}
</script>
