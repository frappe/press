<template>
	<div class="h-screen overflow-auto">
		<iframe
			:src="resourceURL"
			style="width: 100%; height: 100%; border: none"
		></iframe>
	</div>
</template>
<script setup>
import { ref } from 'vue';
import { createResource } from 'frappe-ui';

let resourceURL = ref('');
createResource({
	url: 'press.api.partner.get_resource_url',
	auto: true,
	cache: true,
	onSuccess: (data) => {
		resourceURL.value = data;
	},
});
</script>
