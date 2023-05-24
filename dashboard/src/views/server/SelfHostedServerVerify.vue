<template>
	<div>
		<h2 class="text-lg mb-2">Add this SSH Key to the Server</h2>
		<ClickToCopyField :textContent="ssh_key" />
		<div class="grid my-2 place-items-center">


		</div>
	</div>
</template>
<script>
import ClickToCopyField from '@/components/ClickToCopyField.vue';
export default {
	name: 'SelfHostedServerVerify',
	props: ["ssh_key", "verify"],
	components: {
		ClickToCopyField
	},
	data() {
		return {
			isCopied: false,
			verified: false,
			unreachable: false
		}
	},
	methods: {
	},
}
</script>
