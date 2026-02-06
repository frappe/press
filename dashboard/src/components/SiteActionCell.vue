<template>
	<div class="flex items-center justify-between gap-1">
		<div>
			<h3 class="text-base font-medium">{{ props.actionLabel }}</h3>
			<p class="mt-1 text-p-base text-gray-600">{{ props.description }}</p>
		</div>
		<Button
			v-if="site?.doc"
			class="whitespace-nowrap"
			@click="getSiteActionHandler(props.actionLabel)"
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
import { defineAsyncComponent, h } from 'vue';
import { toast } from 'vue-sonner';
import { confirmDialog, renderDialog } from '../utils/components';
import { getToastErrorMessage } from '../utils/toast';
import router from '../router';
import { isLastSite } from '../data/team';
import CommunicationInfoDialog from './CommunicationInfoDialog.vue';

const props = defineProps({
	siteName: { type: String, required: true },
	actionLabel: { type: String, required: true },
	method: { type: String, required: true },
	description: { type: String, required: true },
	buttonLabel: { type: String, required: true },
	group: { type: String, required: false },
});

const site = getCachedDocumentResource('Site', props.siteName);

function getSiteActionHandler(action) {
	const actionDialogs = {
		'Restore with files': defineAsyncComponent(
			() => import('./SiteDatabaseRestoreDialog.vue'),
		),
		'Restore from an existing site': defineAsyncComponent(
			() => import('./site/SiteDatabaseRestoreFromURLDialog.vue'),
		),
		'Manage database users': defineAsyncComponent(
			() => import('./SiteDatabaseAccessDialog.vue'),
		),
		'Version upgrade': defineAsyncComponent(
			() => import('./site/SiteVersionUpgradeDialog.vue'),
		),
		'Schedule backup': defineAsyncComponent(
			() => import('./site/SiteScheduleBackup.vue'),
		),
	};
	if (actionDialogs[action]) {
		const dialog = h(actionDialogs[action], { site: site.doc.name });
		renderDialog(dialog);
		return;
	}

	const actionHandlers = {
		'Notification Settings': onNotificationSettings,
		'Activate site': onActivateSite,
		'Deactivate site': onDeactivateSite,
		'Drop site': onDropSite,
		'Migrate site': onMigrateSite,
		'Transfer site': onTransferSite,
		'Reset site': onSiteReset,
		'Clear cache': onClearCache,
		'Schedule backup': onScheduleBackup,
	};
	if (actionHandlers[action]) {
		actionHandlers[action].call(this);
	}
}

function onNotificationSettings() {
	return renderDialog(
		h(CommunicationInfoDialog, {
			referenceDoctype: 'Site',
			referenceName: site.doc.name,
		}),
	);
}

function onDeactivateSite() {
	return confirmDialog({
		title: 'Deactivate Site',
		message: `
			Are you sure you want to deactivate this site?<br><br>
			<div class="text-bg-base bg-gray-100 p-2 rounded-md">
			The site will go in an <strong>inactive</strong> state. It won't be accessible and background jobs won't run. 
			<br><br>
			<div class="text-red-600">You will still be charged for it.</div>
			</div>
		`,
		primaryAction: {
			label: 'Deactivate',
			variant: 'solid',
			theme: 'red',
			onClick({ hide }) {
				return site.deactivate.submit().then(hide);
			},
		},
	});
}

function onActivateSite() {
	return confirmDialog({
		title: 'Activate Site',
		message: `
			Are you sure you want to activate this site?
			<br><br>
			<strong>Note: Use this as last resort if site is broken and inaccessible</strong>
		`,
		primaryAction: {
			label: 'Activate',
			variant: 'solid',
			onClick({ hide }) {
				return site.activate.submit().then(hide);
			},
		},
	});
}

function onDropSite() {
	return confirmDialog({
		title: 'Drop Site',
		message: `
            Are you sure you want to drop your site? The site will be archived and
            all of its files and Offsite Backups will be deleted. This action cannot
            be undone.
        `,
		fields: [
			{
				label: 'Please type the site name to confirm.',
				fieldname: 'confirmSiteName',
			},
			{
				label: 'Force drop site',
				fieldname: 'force',
				type: 'checkbox',
			},
		],
		primaryAction: {
			label: 'Drop Site',
			variant: 'solid',
			theme: 'red',
			onClick: async ({ hide, values }) => {
				if (
					![site.doc.name, site.doc.host_name].includes(values.confirmSiteName)
				) {
					throw new Error('Site name does not match.');
				}

				const val = await isLastSite(site.doc.team);
				const FeedbackDialog = defineAsyncComponent(
					() => import('./ChurnFeedbackDialog.vue'),
				);

				return site.archive.submit({ force: values.force }).then(() => {
					hide();
					if (val) {
						renderDialog(
							h(FeedbackDialog, {
								team: site.doc.team,
								onUpdated() {
									router.replace({ name: 'Site List' });
									toast.success('Site dropped successfully');
								},
							}),
						);
					} else {
						router.replace({ name: 'Site List' });
					}
				});
			},
		},
	});
}

function onMigrateSite() {
	return confirmDialog({
		title: 'Migrate Site',
		message: `
            <span class="rounded-sm bg-gray-100 p-0.5 font-mono text-sm font-semibold">bench migrate</span>
            command will be executed on your site. Are you sure you want to run this
            command? We recommend that you take a database backup before continuing.
        `,
		fields: [
			{
				label: 'Skip patches if they fail during migration (Not recommended)',
				fieldname: 'skipFailingPatches',
				type: 'checkbox',
			},
			{
				label: 'Please type the site name to confirm.',
				fieldname: 'confirmSiteName',
			},
		],
		primaryAction: {
			label: 'Migrate',
			variant: 'solid',
			theme: 'red',
			onClick: ({ hide, values }) => {
				if (values.confirmSiteName !== site.doc.name) {
					throw new Error('Site name does not match');
				}
				return site.migrate
					.submit({ skip_failing_patches: values.skipFailingPatches })
					.then(hide);
			},
		},
	});
}

function onSiteReset() {
	return confirmDialog({
		title: 'Reset Site',
		message: `
            All the data from your site will be lost. Are you sure you want to reset your database?
        `,
		fields: [
			{
				label: 'Please type the site name to confirm.',
				fieldname: 'confirmSiteName',
			},
		],
		primaryAction: {
			label: 'Reset',
			variant: 'solid',
			theme: 'red',
			onClick: ({ hide, values }) => {
				if (values.confirmSiteName !== site.doc.name) {
					throw new Error('Site name does not match.');
				}
				return site.reinstall.submit().then(hide);
			},
		},
	});
}

function onTransferSite() {
	return confirmDialog({
		title: 'Transfer Site Ownership',
		fields: [
			{
				label: 'Enter email address of the team for transfer of site ownership',
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
				return site.sendTransferRequest
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

function onClearCache() {
	return confirmDialog({
		title: 'Clear Cache',
		message: `<span class="rounded-sm bg-gray-100 p-0.5 font-mono text-sm font-semibold">bench clear-cache</span> and
            <span class="rounded-sm bg-gray-100 p-0.5 font-mono text-sm font-semibold">bench clear-website-cache</span> commands
            will be executed on your site. Are you sure you want to run these commands?`,
		primaryAction: {
			label: 'Clear Cache',
			variant: 'solid',
			onClick: ({ hide }) => {
				return site.clearSiteCache.submit().then(hide);
			},
		},
	});
}

function onScheduleBackup() {
	router.push({
		name: 'Site Detail Backups',
		params: { name: site.doc.name },
	});
}
</script>
