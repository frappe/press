<template>
	<div class="flex w-1/2 items-center justify-between py-1">
		<div>
			<h3 class="text-base font-medium">{{ props.actionLabel }}</h3>
			<p class="mt-1 text-base text-gray-600">{{ props.description }}</p>
		</div>
		<RestrictedAction
			v-if="site?.doc"
			:doctype="site.doc.doctype"
			:docname="site.doc.name"
			:method="props.method"
			:label="props.buttonLabel"
			@click="getSiteActionHandler(props.actionLabel)"
		/>
	</div>
</template>

<script setup>
import { call, createDocumentResource } from 'frappe-ui';
import { defineAsyncComponent, h } from 'vue';
import { toast } from 'vue-sonner';
import RestrictedAction from '../components/RestrictedAction.vue';
import { renderDialog } from '../utils/components';

const props = defineProps({
	siteName: { type: String, required: true },
	actionLabel: { type: String, required: true },
	method: { type: String, required: true },
	description: { type: String, required: true },
	buttonLabel: { type: String, required: true }
});

const site = createDocumentResource({
	doctype: 'Site',
	name: props.siteName
});

function getSiteActionHandler(action) {
	const actionDialogPaths = {
		'Restore from backup': './SiteDatabaseRestoreDialog.vue',
		'Migrate site': './SiteMigrateDialog.vue',
		'Reset site': './SiteResetDialog.vue',
		'Access site database': './SiteDatabaseAccessDialog.vue',
		Drop: './SiteDropDialog.vue'
	};
	if (actionDialogPaths[action]) {
		const dialog = h(
			defineAsyncComponent(() => import(actionDialogPaths[action])),
			{ site: site.doc.name }
		);
		renderDialog(dialog);
	}

	const actionHandlers = {
		'Activate site': onActivateSite,
		'Deactivate site': onDeactivateSite
	};
	if (actionHandlers[action]) {
		return actionHandlers[action];
	}
}

function onDeactivateSite() {
	return this.$confirm({
		title: 'Deactivate Site',
		message: `
			Are you sure you want to deactivate this site? The site will go in an inactive state.
			It won't be accessible and background jobs won't run. You will <strong>still be charged</strong> for it.
		`,
		actionLabel: 'Deactivate',
		actionColor: 'red',
		async action() {
			return toast.promise(
				call('press.api.site.deactivate', { name: site.doc.name }),
				{
					loading: 'Deactivating site...',
					success: () => {
						setTimeout(() => window.location.reload(), 1000);
						return 'Site deactivated successfully!';
					},
					error: e => {
						return e.messages.length ? e.messages.join('\n') : e.message;
					}
				}
			);
		}
	});
}

function onActivateSite() {
	return this.$confirm({
		title: 'Activate Site',
		message: `
			Are you sure you want to activate this site?
			<br><br>
			<strong>Note: Use this as last resort if site is broken and inaccessible</strong>
		`,
		actionLabel: 'Activate',
		async action() {
			return toast.promise(
				call('press.api.site.activate', { name: site.doc.name }),
				{
					loading: 'Activating site...',
					success: () => {
						setTimeout(() => window.location.reload(), 1000);
						return 'Site activated successfully!';
					},
					error: e => {
						return e.messages.length ? e.messages.join('\n') : e.message;
					}
				}
			);
		}
	});
}
</script>
