<template>
	<div>
		<h2 class="text-lg font-semibold space-y-1">Enter the Server Details</h2>
		<div class="mt-6 flex flex-col gap-4">
			<p class="text-base text-black-900">Public IP of the Server</p>
			<Input
				class="z-10 w-full rounded-r-none"
				:value="publicIP"
				@change="$emit('update:publicIP', $event)"
				type="text"
			/>
			<p class="text-base text-black-900">Private IP of the Server</p>
			<Input
				class="z-10 w-full rounded-r-none"
				:value="privateIP"
				@change="$emit('update:privateIP', $event)"
				type="text"
			/>
			<div class="mt-4">
				<ErrorMessage :message="publicIpErrorMessage" />
				<ErrorMessage :message="privateIpErrorMessage" />
			</div>
		</div>
	</div>
</template>
<script>
export default {
	name: 'SelfHostedServerForm',
	props: ['privateIP', 'publicIP', 'error'],
	emits: ['update:publicIP', 'update:privateIP', 'update:error'],
	watch: {
		hasError() {
			this.$emit('update:error', this.hasError);
		}
	},
	mounted() {
		this.$emit('update:error', this.hasError);
	},
	computed: {
		privateIpErrorMessage() {
			return this.validateIP(this.privateIP, 'Private');
		},
		publicIpErrorMessage() {
			return this.validateIP(this.publicIP, 'Public');
		},
		hasError() {
			return (
				this.privateIpErrorMessage !== null ||
				this.publicIpErrorMessage !== null
			);
		}
	},
	methods: {
		validateIP(ip, type) {
			try {
				console.log('Validation Point');
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
