<template>
	<div>
		<h2 class="space-y-1 text-lg font-semibold">
			Enter the App Server Details
		</h2>
		<div class="mt-6 flex flex-col gap-4">
			<p class="text-black-900 text-base">Public IP of the Server</p>
			<FormControl
				class="z-10 w-full rounded-r-none"
				:value="publicIP"
				@change="$emit('update:publicIP', $event.target.value)"
			/>
			<p class="text-black-900 text-base">Private IP of the Server</p>
			<FormControl
				class="z-10 w-full rounded-r-none"
				:value="privateIP"
				@change="$emit('update:privateIP', $event.target.value)"
			/>
			<div class="mt-1">
				<ErrorMessage :message="publicIpErrorMessage" />
			</div>
		</div>
		<h2 class="space-y-1 mt-4 text-lg font-semibold">
			Enter the DB Server Details
		</h2>
		<div class="mt-6 flex flex-col gap-4">
			<p class="text-black-900 text-base">Public IP of the DB Server</p>
			<FormControl
				class="z-10 w-full rounded-r-none"
				:value="dbpublicIP"
				@change="$emit('update:dbpublicIP', $event.target.value)"
			/>
			<p class="text-black-900 text-base">Private IP of the DB Server</p>
			<FormControl
				class="z-10 w-full rounded-r-none"
				:value="dbprivateIP"
				@change="$emit('update:dbprivateIP', $event.target.value)"
			/>
		</div>
		<div class="mb-3"></div>
	</div>
</template>
<script>
export default {
	name: 'SelfHostedServerForm',
	props: ['publicIP', 'dbpublicIP', 'dbprivateIP', 'privateIP', 'error'],
	emits: [
		'update:publicIP',
		'update:dbpublicIP',
		'update:dbprivateIP',
		'update:privateIP',
		'update:error'
	],
	watch: {
		hasError() {
			this.$emit('update:error', this.hasError);
		}
	},
	mounted() {
		this.$emit('update:error', this.hasError);
	},
	computed: {
		publicIpErrorMessage() {
			return this.validateIP(this.publicIP, 'Public');
		},
		hasError() {
			return this.publicIpErrorMessage !== null;
		}
	},
	methods: {
		validateIP(ip, type) {
			try {
				const stripped_ip = ip.replace(/\s+/g, '');
				const ipAddressRegex = /^([0-9]{1,3}\.){3}[0-9]{1,3}$/;
				const ver = ipAddressRegex.test(stripped_ip);
				return ver ? null : `${type} IP is invalid`;
			} catch {
				return `${type} IP cannot be blank`;
			}
		}
	}
};
</script>
