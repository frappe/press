<template>
	<Button
		v-if="show"
		v-bind="buttonProps"
		variant="subtle"
		@click="
			() => {
				renderDialog(
					h(DialogComponent, {
						doctype,
						docname,
						onOpenRequestDialog: () => {
							renderDialog(
								h(AccessRequestDialog, {
									doctype,
									docname,
								}),
							);
						},
					}),
				);
			}
		"
	/>
</template>

<script setup lang="ts">
import { computed, h } from 'vue';
import { getTeam } from '../data/team';
import { renderDialog } from '../utils/components';
import AccessRequestDialog from './AccessRequestDialog.vue';
import AccessRequestStatusDialog from './AccessRequestStatusDialog.vue';

const props = defineProps<{
	doctype: string;
	docname: string;
	doc?: any;
	error?: Error;
}>();

const team = getTeam();

const buttonProps = computed(() => {
	if (props.doc) {
		return {
			label: '',
			icon: 'unlock',
		};
	} else {
		return {
			label: 'Request Access',
			iconLeft: 'lock',
		};
	}
});

const isError = computed(() => {
	return Boolean(props.error?.message);
});

const isPermissionError = computed(() => {
	return Boolean(props.error?.message.endsWith('PermissionError'));
});

const canRequestAccess = computed(() => {
	return Boolean(team.doc?.can_request_access);
});

const isOwner = computed(() => {
	return props.doc?.team === team.doc?.name;
});

const hasAccess = computed(() => {
	return !isOwner.value && !isError.value;
});

const DialogComponent = computed(() => {
	if (props.doc) {
		return AccessRequestStatusDialog;
	} else {
		return AccessRequestDialog;
	}
});

const show = computed(() => {
	return canRequestAccess.value && (isPermissionError.value || hasAccess.value);
});
</script>
