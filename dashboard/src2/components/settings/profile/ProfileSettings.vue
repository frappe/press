<template>
	<div class="p-5">
		<div class="space-y-5">
			<AccountProfile />
			<AccountReferral />
			<AccountPartner />
			<AccountEmails />
		</div>
	</div>
</template>

<script setup>
import AccountProfile from './AccountProfile.vue';
import AccountReferral from './AccountReferral.vue';
import AccountPartner from './AccountPartner.vue';
import AccountEmails from './AccountEmails.vue';

document.title = 'Settings - Profile';
</script>
