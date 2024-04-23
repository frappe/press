<template>
	<div class="space-y-5 p-5">
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

document.title = 'Settings - Profile';
</script>
