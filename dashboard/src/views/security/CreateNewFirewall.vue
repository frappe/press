<template>
	<div>
		<div class="mx-5 mt-5">
			<div class="flex">
				<div class="flex w-full justify-between space-x-2 pb-4">
					<label class="text-lg font-semibold"> Create Firewall </label>
				</div>
				<Button
					variant="solid"
					class="justify-end"
					label="Save"
					@click="createFirewall"
				>
				</Button>
			</div>
		</div>
		<div class="mx-5 mt-10">
			<div class="flex">
				<div class="flex w-full space-x-2 pb-4">
					<div>
						<label class="text-lg font-semibold"> Name </label>
						<FormControl class="mt-2" v-model="benchTitle" />
					</div>
				</div>
			</div>
			<div class="mx-2.5 border-b" />
			<div class="mt-5">
				<label class="text-lg font-semibold"> Inbound Rules </label>
			</div>
			<FirewallRuleView
				:rules="newRules"
				:disableSearch="true"
			></FirewallRuleView>
			<div class="mx-2.5 border-b" />
			<div class="mx-5 mt-5">
				<Button
					variant="solid"
					icon-left="plus"
					class="ml-2"
					label="Add Rule"
					@click="showFirewallRuleDialog = true"
				>
				</Button>
			</div>
		</div>
		<FirewallRuleDialog
			:server="server"
			:rules="newRules"
			v-model="showFirewallRuleDialog"
			v-if="showFirewallRuleDialog"
		/>
	</div>
</template>

<script>
import FirewallRuleView from './FirewallRuleView.vue';
import { defineAsyncComponent } from 'vue';

export default {
	name: 'CreateNewFirewall',
	props: ['server', 'firewallName'],
	components: {
		FirewallRuleView,
		FirewallRuleDialog: defineAsyncComponent(() =>
			import('./FirewallRuleDialog.vue')
		)
	},
	methods: {
		getRoute() {
			return `/security/${this.server.name}/firewall/`;
		},
		createFirewall() {
			alert('create firewall');
		}
	},
	data() {
		return {
			showFirewallRuleDialog: false,
			newRules: []
		};
	}
};
</script>
