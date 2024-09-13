<template>
	<div class="p-5">
		<div class="space-y-5">
			<AccountProfile />
			<AccountReferral />
			<AccountPartner />
		</div>
	</div>
</template>

<script setup>
import AccountProfile from './AccountProfile.vue';
import AccountReferral from './AccountReferral.vue';
import AccountPartner from './AccountPartner.vue';

document.title = 'Settings - Profile';
</script>
