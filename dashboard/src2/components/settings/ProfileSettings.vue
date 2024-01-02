<template></template>

<script setup>
import { inject } from 'vue';
const breadcrumbs = inject('breadcrumbs');
breadcrumbs.value = [
	{ label: 'Settings', route: '/settings' },
	{ label: 'Profile', route: '/settings/profile' }
];
</script>