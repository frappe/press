<template>
	<div>
		<h2 class="text-lg font-semibold space-y-1">Enter the Server Details</h2>
		<div class="mt-6 flex flex-col gap-4">
			<p class="text-base text-black-900">Public IP of the Server </p>
			<Input :value="public_ip" @change="$emit('update:public_ip', $event)" @input="verifyIP" type="text" />
			<p class="text-base text-black-900"> Private IP of the Server</p>
			<Input :value="private_ip" @change="$emit('update:private_ip', $event)" type="text" @input="verifyIP" />
		</div>
	</div>
</template>
<script>
import Input from 'frappe-ui/src/components/Input.vue';
export default {
	name: 'SelfHostedServerForm',
	props: ["private_ip", "public_ip"],
	emits: ['update:public_ip', 'update:private_ip'],
	components: {
		Input
	},
	methods: {
		verifyIP(e) {
			console.log("Ivde", e)
			const ipAddressRegex = /^([0-9]{1,3}\.){3}[0-9]{1,3}$/;
			const ver = ipAddressRegex.test(e)
			if (ver) {
				console.log("Verified", e)
			} else {
				console.log("Not Verified")
			}
		}
	},
};
</script>
