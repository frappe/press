<template>
	<div>
		<div class="mx-5 mt-5">
			<div class="flex">
				<div class="flex w-full justify-between space-x-2 pb-4">
					<label class="text-lg font-semibold" v-if="!firewallId">
						Create Firewall
					</label>
					<label class="text-lg font-semibold" v-else> Update Firewall </label>
				</div>
				<Button
					variant="solid"
					class="justify-end"
					label="Save"
					@click="
						!firewallId
							? $resources.createFirewall.submit()
							: $resources.updateFirewall.submit()
					"
				>
				</Button>
			</div>
		</div>
		<div class="mx-5 mt-10">
			<div class="flex">
				<div class="flex w-full space-x-2 pb-4">
					<div>
						<label class="text-lg font-semibold"> Name </label>
						<FormControl
							class="mt-2"
							v-model="firewallName"
							:readonly="firewallId"
						/>
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
	name: 'CreateUpdateFirewall',
	props: ['server', 'firewallId'],
	components: {
		FirewallRuleView,
		FirewallRuleDialog: defineAsyncComponent(() =>
			import('./FirewallRuleDialog.vue')
		)
	},
	methods: {
		getRoute() {
			return `/security/${this.server.name}/firewall/`;
		}
	},
	resources: {
		createFirewall() {
			return {
				url: 'press.api.security.create_firewall',
				params: {
					server: this.server?.name,
					server_type: this.server?.server_type,
					firewall_name: this.firewallName,
					firewall_rules: this.newRules
				},
				onSuccess: () => {
					console.log(this.$router);
					this.$router.push(`/security/${this.server.name}/firewall`);
				}
			};
		},
		updateFirewall() {
			return {
				url: 'press.api.security.update_firewall',
				params: {
					server: this.server?.name,
					server_type: this.server?.server_type,
					firewall_rules: this.newRules,
					firewall_name: this.firewallId
				},
				onSuccess: () => {
					console.log(this.$router);
					this.$router.push(`/security/${this.server.name}/firewall`);
				}
			};
		},
		fetchFirewallInfo() {
			return {
				url: 'press.api.security.fetch_firewall_and_rules',
				params: {
					server: this.server?.name,
					server_type: this.server?.server_type
				},
				auto: true,
				onSuccess: () => {
					this.newRules = this.$resources.fetchFirewallInfo.data.rules || [];
				}
			};
		}
	},
	data() {
		return {
			showFirewallRuleDialog: false,
			newRules: [],
			firewallName: this.firewallId || ''
		};
	}
};
</script>
