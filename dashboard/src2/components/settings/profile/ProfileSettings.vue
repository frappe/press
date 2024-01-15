<template>
	<div class="p-5 space-y-5">
		<AccountProfile />
		<AccountEmails />
		<AccountReferral />
	</div>
</template>

<script setup>
import AccountEmails from './AccountEmails.vue';
import AccountProfile from './AccountProfile.vue';
import AccountReferral from './AccountReferral.vue';

import { inject } from 'vue';
const breadcrumbs = inject('breadcrumbs');
breadcrumbs.value = [
	{ label: 'Settings', route: '/settings' },
	{ label: 'Profile', route: '/settings/profile' }
];

document.title = 'Settings - Profile';
</script>
