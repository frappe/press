<template>
	<Tooltip
		:text="
			!hasMethodPermission.data
				? `You don't have enough permissions to perform this action`
				: null
		"
	>
		<slot v-bind="{ hasMethodPermission: hasMethodPermission.data }">
			<Button v-bind="$attrs" :disabled="!hasMethodPermission.data"></Button>
		</slot>
	</Tooltip>
</template>

<script setup>
import { Button, createResource, Tooltip } from 'frappe-ui';
import { getTeam } from '../data/team';

const props = defineProps({
	doctype: { type: String, required: true },
	docname: { type: String, required: true },
	method: { type: String, required: true }
});

const hasMethodPermission = createResource({
	url: 'press.api.account.has_method_permission',
	params: {
		doctype: props.doctype,
		docname: props.docname,
		method: props.method
	},
	cache: [
		'SiteActionPermission',
		getTeam().doc.name,
		props.doctype,
		props.docname,
		props.method
	],
	auto: true
});
</script>
