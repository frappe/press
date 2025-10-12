<template>
	<div v-if="error" class="mx-auto space-y-4 text-center w-fit">
		<p class="text-sm font-medium">
			You do not have permission to view this resource
		</p>
		<Button
			v-if="canRequestAccess"
			variant="solid"
			label="Request Access"
			@click="
				() =>
					renderDialog(
						h(AccessRequestDialog, {
							doctype,
							docname,
						}),
					)
			"
		/>
	</div>
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
	return props.error?.message.endsWith('PermissionError');
});
const canRequestAccess = isPermissionError && team.doc.can_request_access;
</script>
