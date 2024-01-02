<template>
	<div class="flex flex-wrap gap-x-4 gap-y-2 text-base max-w-[36rem] lg:max-w-[56rem]">
		<div class="mb-2 mr-4 flex w-[12rem] items-center truncate">
			<FormControl
				type="checkbox"
				:label="hasAllPermissions ? 'Deny All' : 'Allow All'"
				:modelValue="hasAllPermissions"
				@update:modelValue="
					$emit('permissionChange', { method: '*', permitted: $event })
				"
			/>
		</div>
		<div
			v-for="(perm, idx) in permissions"
			:key="idx"
			class="mb-2 mr-4 flex w-[12rem] items-center truncate"
		>
			<FormControl
				type="checkbox"
				:label="perm.label"
				:modelValue="perm.permitted"
				@update:modelValue="
					emit('permissionChange', { method: perm.method, permitted: $event })
				"
			/>
		</div>
	</div>
</template>

<script setup>
import { FormControl } from 'frappe-ui';
import { computed } from 'vue';

const emit = defineEmits(['permissionChange']);
const props = defineProps({
	permissions: {
		type: Object,
		required: true
	}
});
const permissions = computed(() => {
	return props.permissions.sort((a, b) => a.label.localeCompare(b.label));
});
const hasAllPermissions = computed(() => {
	return permissions.value.every(perm => perm.permitted);
});
</script>
