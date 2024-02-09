<template>
	<div class="p-5 space-y-5">
		<div class="grid grid-cols-1 items-start gap-5 sm:grid-cols-2">
			<AccountProfile />
			<AccountEmails />
			<AccountReferral />
			<AccountPartner />
		</div>
	</div>
</template>

<script setup>
import AccountEmails from './AccountEmails.vue';
import AccountProfile from './AccountProfile.vue';
import AccountReferral from './AccountReferral.vue';
import AccountPartner from './AccountPartner.vue';

import { inject } from 'vue';
const breadcrumbs = inject('breadcrumbs');
breadcrumbs.value = [
	{ label: 'Settings', route: '/settings' },
	{ label: 'Profile', route: '/settings/profile' }
];

document.title = 'Settings - Profile';
</script>
