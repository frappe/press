<template>
	<Button
		v-if="canRequestAccess"
		label="Request Access"
		icon-left="lock"
		variant="subtle"
		@click="
			() => {
				renderDialog(
					h(AccessRequestDialog, {
						doctype,
						docname,
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

const props = defineProps<{
	doctype: string;
	docname: string;
	error?: Error;
}>();

const team = getTeam();

const isPermissionError = computed(() => {
	return Boolean(props.error?.message.endsWith('PermissionError'));
});

const canRequestAccess = computed(() => {
	return Boolean(isPermissionError.value && team.doc?.can_request_access);
});
</script>
