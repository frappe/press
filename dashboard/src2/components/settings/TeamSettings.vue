<template>
	<div class="grid grid-cols-1 items-start gap-5 p-4 sm:grid-cols-2">
		<div class="rounded-md border">
			<div class="h-12 border-b px-5 py-4">
				<h2 class="text-lg font-medium text-gray-900">Members</h2>
			</div>
			<div>
			</div>
		</div>
		<div class="rounded-md border">
			<div class="flex h-12 items-center justify-between border-b px-5">
				<h2 class="text-lg font-medium text-gray-900">Groups</h2>
				<Button iconLeft="plus" @click="">New Group</Button>
			</div>
			<div class="">
			</div>
		</div>
	</div>
</template>

<script setup>
import { inject, ref } from 'vue';

const breadcrumbs = inject('breadcrumbs');
breadcrumbs.value = [
	{ label: 'Settings', route: '/settings' },
	{ label: 'Team', route: '/settings/team' }
];
</script>
