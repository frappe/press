<template>
	<div>
		<h2 class="text-lg font-semibold space-y-1">Enter the Server Details</h2>
		<div class="mt-6 flex flex-col gap-4">
			<p class="text-base text-black-900">Public IP of the Server </p>
			<Input :value="publicIp" @change="$emit('update:publicIp', $event)" @input="verifyIP($event,'publicIp')" type="text" />
			<ErrorMessage class="my-1" v-if="validPublicIP" message="Public IP is invalid"/>
			<p class="text-base text-black-900"> Private IP of the Server</p>
			<Input :value="privateIp" @change="$emit('update:privateIp', $event)" type="text" @input="verifyIP($event,'privateIp')" />
			<ErrorMessage v-if="validPrivateIP" message="Private IP is invalid"/>
		</div>

	</div>
</template>
<script>
export default {
	name: 'SelfHostedServerForm',
	props: ["privateIp", "publicIp"],
	emits: ['update:publicIp', 'update:privateIp'],
	data(){
		return{
			validPublicIP:false,
			validPrivateIP:false
		}
	},
	methods: {
		verifyIP(e,type) {
			console.log("Ivde", e, type)
			const ipAddressRegex = /^([0-9]{1,3}\.){3}[0-9]{1,3}$/;
			const ver = ipAddressRegex.test(e)
			if (ver) {
				if(type==="publicIp"){
					this.validPublicIP = false
				}else{
					this.validPrivateIP = false
				}
			} else {
				if(type==="publicIp"){
					this.validPublicIP = true
				}else{
					this.validPrivateIP = true
				}
			}
		}
	},
};
</script>
