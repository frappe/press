<template>
	<component
		:is="!hasMethodPermission.data ? 'Tooltip' : 'div'"
		:text="
			!hasMethodPermission.data
				? `You don't have enough permissions to perform this action`
				: null
		"
	>
		<slot v-bind="{ hasMethodPermission: hasMethodPermission.data }">
			<Button
				class="whitespace-nowrap"
				v-bind="$attrs"
				:disabled="!hasMethodPermission.data"
			></Button>
		</slot>
	</component>
</template>

<script setup>
import { Button, createResource, Tooltip } from 'frappe-ui';
import { getTeam } from '../data/team';
import session from '../data/session';

defineOptions({ inheritAttrs: false });

const props = defineProps({
	doctype: { type: String, required: true },
	docname: { type: String, required: true },
	method: { type: String, required: true }
});

if (!props.doctype || !props.docname || !props.method) {
	console.warn('doctype, docname and method are required');
}

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
		session.user,
		props.doctype,
		props.docname,
		props.method
	],
	auto: true
});
</script>
