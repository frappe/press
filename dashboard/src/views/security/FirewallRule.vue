<template>
	<div class="py-2 text-base text-gray-600 sm:px-2" v-if="rules.length === 0">
		No firewall rules configured
	</div>
	<div v-for="(rule, index) in rules" :key="rule.from_port">
		<div class="flex items-center rounded hover:bg-gray-100">
			<div class="w-full px-3 py-4">
				<div class="flex items-center">
					<div class="w-2/12 text-base font-medium">
						{{ rule.protocol }}
					</div>
					<div class="w-2/12 text-base font-medium">
						{{ rule.port_range }}
					</div>
					<div class="w-2/12 text-base font-medium">
						{{ rule.source }}
					</div>
					<div class="w-2/12 text-base font-medium">
						{{ rule.action }}
					</div>
					<div class="w-4/12">
						{{ rule.description }}
					</div>
				</div>
			</div>
			<Dropdown
				:options="dropdownItems(rule)"
				v-if="rule.firewall_status == 'Enabled'"
			>
				<template v-slot="{ open }">
					<Button variant="ghost" class="mr-2" icon="more-horizontal" />
				</template>
			</Dropdown>
		</div>
		<div
			class="translate-y-2 transform"
			:class="{ 'border-b': index < rules.length - 1 }"
		/>
	</div>
</template>
<script>
export default {
	name: 'FirewallRule',
	props: ['servers', 'rules'],
	methods: {
		dropdownItems(rule) {
			return [
				{
					label: 'Delete Rule',
					onClick: () => {
						alert(this.rule.name);
					}
				}
			];
		}
	}
};
</script>
