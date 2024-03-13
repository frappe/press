<template>
	<div>
		<h2 class="space-y-1 mt-4 text-lg font-semibold">Choose setup type</h2>
		<div class="mt-6 flex flex-col gap-4">
			<FormControl
				class="mr-8"
				type="select"
				:options="setupTypeOptions()"
				:value="setupType"
				@change="$emit('update:setupType', $event.target.value)"
			/>
		</div>
		<div class="mb-3">
			<div v-if="setupType">
				<h2
					v-if="isMultiserverSetup()"
					class="space-y-1 mt-6 text-lg font-semibold"
				>
					Enter the App Server Details
				</h2>
				<h2 v-else class="space-y-1 mt-6 text-lg font-semibold">
					Enter the Server Details
				</h2>

				<div class="mt-6 flex flex-col gap-4">
					<p class="text-black-900 text-base">Public IP of the Server</p>
					<FormControl
						class="z-10 w-full rounded-r-none"
						:value="publicIP"
						@change="$emit('update:publicIP', $event.target.value)"
					/>
					<ErrorMessage class="text-sm" :message="publicIpErrorMessage" />

					<p class="text-black-900 text-base">Private IP of the Server</p>
					<FormControl
						class="z-10 w-full rounded-r-none"
						:value="privateIP"
						@change="$emit('update:privateIP', $event.target.value)"
					/>
					<ErrorMessage class="text-sm" :message="privateIpErrorMessage" />
				</div>
			</div>
			<div v-if="isMultiserverSetup()">
				<h2 class="space-y-1 mt-4 text-lg font-semibold">
					Enter the DB Server Details
				</h2>
				<div class="mt-6 flex flex-col gap-4">
					<p class="text-black-900 text-base">Public IP of the DB Server</p>
					<FormControl
						class="z-10 w-full rounded-r-none"
						:value="dbPublicIP"
						@change="$emit('update:dbPublicIP', $event.target.value)"
					/>
					<ErrorMessage class="text-sm" :message="dbPublicIpErrorMessage" />

					<p class="text-black-900 text-base">Private IP of the DB Server</p>
					<FormControl
						class="z-10 w-full rounded-r-none"
						:value="dbPrivateIP"
						@change="$emit('update:dbPrivateIP', $event.target.value)"
					/>
					<ErrorMessage class="text-sm" :message="dbPrivateIpErrorMessage" />
				</div>
			</div>
		</div>
	</div>
</template>
<script>
export default {
	name: 'SelfHostedServerForm',
	props: [
		'publicIP',
		'dbPublicIP',
		'dbPrivateIP',
		'privateIP',
		'error',
		'setupType'
	],
	emits: [
		'update:publicIP',
		'update:dbPublicIP',
		'update:dbPrivateIP',
		'update:privateIP',
		'update:error',
		'update:setupType'
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
		dbPublicIpErrorMessage() {
			return this.validateIP(this.dbPublicIP, 'DB Public');
		},
		privateIpErrorMessage() {
			return this.validateIP(this.privateIP, 'Private');
		},
		dbPrivateIpErrorMessage() {
			return this.validateIP(this.dbPrivateIP, 'DB Private');
		},
		hasError() {
			console.log(this.publicIpErrorMessage, this.privateIpErrorMessage);
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
		},
		setupTypeOptions() {
			return [
				{ value: 'standalone', label: 'Standalone' },
				{ value: 'multiserver', label: 'Multiserver' }
			];
		},
		isMultiserverSetup() {
			return this.setupType === 'multiserver';
		}
	}
};
</script>
