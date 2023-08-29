<template>
	<Dialog
		:options="{
			title: 'Firewall Rule',
			actions: [
				{
					label: 'Add',
					variant: 'solid',
					onClick: () => addRule()
				}
			]
		}"
		v-model="showDialog"
	>
		<template v-slot:body-content>
			<FormControl
				class="mb-4"
				label="Protocol"
				type="select"
				:options="protocolOptions"
				v-model="protocol"
				required
			/>
			<FormControl
				class="mb-0.5"
				label="Port Range"
				type="text"
				v-model="port_range"
				required
				@change="validPortRange"
			/>
			<p class="mb-4 text-sm text-gray-600">
				Enter a single port or a range of ports. Example: 80 or 8000-9000
			</p>
			<ErrorMessage class="mb-4" :message="portError" />

			<FormControl
				class="mb-4"
				label="Source Type"
				type="select"
				:options="sourceTypeOptions"
				v-model="source_type"
				required
				@change="toggleSource"
			/>
			<FormControl
				class="mb-4"
				label="Source"
				type="text"
				v-model="source"
				v-if="this.isCustomSource"
				@change="validateIPv4v6"
			/>
			<ErrorMessage class="mb-4" :message="invalidIPError" />
			<FormControl
				class="mb-4"
				label="Action"
				type="select"
				:options="actionOptions"
				v-model="action"
				required
			/>
			<FormControl
				class="mb-4"
				label="Description"
				type="text"
				v-model="description"
				required
			/>
		</template>
	</Dialog>
</template>
<script>
export default {
	name: 'FirewallRuleDialog',
	props: ['server', 'modelValue', 'rules'],
	emits: ['update:modelValue', 'success'],
	data() {
		return {
			isCustomSource: false,
			portError: '',
			invalidIPError: '',
			protocol: '',
			port_range: '',
			source: '',
			description: '',
			actionOptions: [
				{
					label: 'Allow',
					value: 'Allow'
				},
				{
					label: 'Deny',
					value: 'Deny'
				}
			],
			protocolOptions: [
				{
					label: '',
					value: ''
				},
				{
					label: 'TCP',
					value: 'TCP'
				},
				{
					label: 'UDP',
					value: 'UDP'
				},
				{
					label: 'ICMP',
					value: 'ICMP'
				}
			],
			sourceTypeOptions: [
				{
					label: '',
					value: ''
				},
				{
					label: 'Custom',
					value: 'Custom'
				},
				{
					label: 'All IPv4',
					value: 'All IPv4'
				},
				{
					label: 'All IPv6',
					value: 'All IPv6'
				},
				{
					label: 'All IPv4 & IPv6',
					value: 'All IPv4 & IPv6'
				}
			],
			error: ''
		};
	},
	methods: {
		validPortRange() {
			this.portError = '';

			if (this.port_range == '') {
				this.portError = 'Port Range is required';

				return false;
			}

			if (this.port_range.includes('-')) {
				const [from, to] = this.port_range.split('-');

				if (from > to) {
					this.portError = 'Invalid port range';
					return false;
				}
			}

			let regex = '^[0-9-]+$';

			if (!this.port_range.match(regex)) {
				this.portError = 'Invalid port range';
				return false;
			}

			return true;
		},

		validateIPv4v6() {
			let ipv4_regex =
				'^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$';
			let ipv6_regex =
				'^((([0-9A-Fa-f]{1,4}:){1,6}:)|(([0-9A-Fa-f]{1,4}:){7}))([0-9A-Fa-f]{1,4})$';

			this.invalidIPError = '';
			if (this.source_type == 'Custom') {
				if (!this.source.match(ipv4_regex) && !this.source.match(ipv6_regex)) {
					this.invalidIPError = 'Invalid IP address';
					return false;
				}
			}

			return true;
		},

		addRule() {
			if (this.source_type != 'Custom') {
				this.source = this.source_type;
			}

			if (!this.validPortRange()) {
				return;
			}

			this.rules.push({
				protocol: this.protocol,
				port_range: this.port_range,
				source: this.source,
				source_type: this.source_type,
				description: this.description,
				action: this.action
			});

			this.showDialog = false;
		},

		toggleSource() {
			this.isCustomSource = this.source_type == 'Custom';
		}
	},
	computed: {
		showDialog: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		}
	}
};
</script>
