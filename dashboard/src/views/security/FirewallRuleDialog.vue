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
				class="mb-3"
				label="Protocol"
				type="select"
				:options="protocolOptions"
				v-model="protocol"
				required
			/>
			<FormControl
				class="mb-3"
				label="Port Range"
				type="text"
				v-model="port_range"
				required
			/>
			<FormControl
				class="mb-3"
				label="Source Type"
				type="select"
				:options="sourceTypeOptions"
				v-model="source_type"
				required
				@change="changeSource"
			/>
			<FormControl
				class="mb-3"
				label="Source"
				type="text"
				v-model="source"
				v-if="this.isCustomSource"
			/>
			<FormControl
				class="mb-3"
				label="Action"
				type="select"
				:options="actionOptions"
				v-model="action"
				required
			/>
			<FormControl
				class="mb-3"
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
			]
		};
	},
	methods: {
		addRule() {
			if (this.source_type != 'Custom') {
				this.source = this.source_type;
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

		changeSource() {
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
