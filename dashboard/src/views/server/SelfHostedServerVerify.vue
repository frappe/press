<template>
	<div>
		<div class="my-2">
			<span class="text-base">Add this SSH Key to
				<span class="font-mono text-blue-500">~/.ssh/known_hosts</span> of the
				Server you are adding</span>
		</div>
		<ClickToCopyField :textContent="ssh_key" />
		<div class="grid my-2 place-items-center"></div>
	</div>
</template>
<script>
import ClickToCopyField from '@/components/ClickToCopyField.vue';
export default {
	name: 'SelfHostedServerVerify',
	props: ['ssh_key'],
	components: {
		ClickToCopyField
	}
};
</script>
