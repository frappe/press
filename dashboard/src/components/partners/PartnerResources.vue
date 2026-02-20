<template>
	<div class="h-screen overflow-auto">
		<iframe
			:src="resourceURL.data"
			style="width: 100%; height: 100%; border: none"
		></iframe>
	</div>
</template>
<script setup>
import { createResource } from 'frappe-ui';

const resourceURL = createResource({
	url: 'press.api.partner.get_resource_url',
	auto: true,
	cache: true,
});
</script>
