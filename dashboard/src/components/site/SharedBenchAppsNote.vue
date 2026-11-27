<template>
	<div
		v-if="site.doc?.group_public"
		class="mt-4 flex flex-wrap items-center justify-between gap-3 rounded border bg-surface-gray-1 p-3 text-base"
	>
		<p class="min-w-0 flex-1 text-ink-gray-7">
			This site is on a shared bench group, so the list shows only the apps of
			that group. To install another app, such as your own app or a
			Marketplace app that is not in the list, move the site to a private bench
			group.
			<template v-if="!canMove">
				Your current plan does not allow a private bench group.
			</template>
		</p>
		<Button
			class="shrink-0"
			:label="canMove ? 'Move to Private Bench' : 'Change Plan'"
			@click="canMove ? moveToPrivateBench() : changePlan()"
		/>
	</div>
</template>

<script setup>
import { getCachedDocumentResource } from 'frappe-ui';
import { computed, defineAsyncComponent, h } from 'vue';
import { renderDialog } from '../../utils/components';

const props = defineProps({
	site: { type: String, required: true },
});
const emit = defineEmits(['close']);

const site = getCachedDocumentResource('Site', props.site);
const canMove = computed(() => Boolean(site.doc?.current_plan?.private_benches));

function moveToPrivateBench() {
	emit('close');
	const SiteMigrationDialog = defineAsyncComponent(
		() => import('./SiteMigration.vue'),
	);
	renderDialog(
		h(SiteMigrationDialog, {
			site: props.site,
			defaultAction: 'Move Site To Different Server / Bench',
			defaultNewBenchName: site.doc?.group_title
				? `${site.doc.group_title} - Cloned`
				: null,
		}),
	);
}

function changePlan() {
	emit('close');
	const ManageSitePlansDialog = defineAsyncComponent(
		() => import('../ManageSitePlansDialog.vue'),
	);
	renderDialog(h(ManageSitePlansDialog, { site: props.site }));
}
</script>
