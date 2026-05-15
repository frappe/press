<script setup>
import { Badge, Avatar } from 'frappe-ui';
</script>

<template>
	<div class="flex flex-col gap-2">
		<Avatar image="https://via.placeholder.com/150" size="lg" />
		<p class="text-p-base font-semibold text-ink-gray-8">Company Name</p>
		<Badge variant="subtle" theme="green" size="lg">Active</Badge>
	</div>
	<div class="flex justify-start items-center">
		<Button variant="subtle" theme="primary">Complete Profile</Button>
	</div>
</template>
