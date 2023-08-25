<template>
	<div>
		<div class="mx-5 mt-5" v-if="firewall.disabled">
			<Alert>
				<div>
					<span>
						Before activating systems firewall, disable firewall rules (if
						configured on cloud service provider console)
					</span>
				</div>
				<template #actions>
					<Button
						variant="outline"
						theme="gray"
						appearance="primary"
						@click="$router.push(`/security/${this.server.name}/firewall/new`)"
					>
						Create Firewall</Button
					>
				</template>
				<FirewallRuleDialog
					:server="server"
					v-model="enableFirewall"
					v-if="enableFirewall"
				/>
			</Alert>
		</div>
		<div class="mx-5 mt-5" v-else>
			<LoadingText v-if="$resources.FirewallRules.loading" />
			<FirewallRuleView :rules="rules" v-else />
			<div class="mx-2.5 border-b" />
		</div>
		<div class="mx-5 mt-15">
			<div class="block w-full">
				<div
					class="items-start rounded-md px-4 py-3.5 text-base md:px-5 text-gray-700 bg-gray-50"
				>
					Example:
					<div class="mt-5">
						<FirewallRuleView
							:rules="this.getExmpleRule()"
							:disableSearch="true"
							:disableAction="true"
						/>
					</div>
					<div class="mx-2.5 border-b" />
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import FirewallRuleView from './FirewallRuleView.vue';

export default {
	name: 'Firewall',
	props: ['server', 'firewallName'],
	components: {
		FirewallRuleView
	},
	resources: {
		FirewallRules() {
			return {
				method: 'press.api.security.get_firewall_rules',
				params: {
					server: this.server?.name,
					server_type: this.server?.server_type
				},
				auto: true,
				onError: this.$routeTo404PageIfNotFound
			};
		}
	},
	methods: {
		getExmpleRule() {
			return [
				{
					action: 'Allow',
					description: 'HTTP from anywhere',
					from_port: 80,
					port_range: '80',
					protocol: 'TCP',
					service: 'HTTP',
					source: '0.0.0.0/0',
					source_type: 'Custom',
					to_port: 80
				},
				{
					action: 'Allow',
					description: 'SSH from 127.0.1.2',
					from_port: 22,
					port_range: '22',
					protocol: 'TCP',
					service: 'HTTP',
					source: '127.0.1.2',
					source_type: 'Custom',
					to_port: 22
				}
			];
		},
		updateRoute() {
			return `/security/${this.server.name}/firewall/create`;
		}
	},
	computed: {
		rules() {
			return this.$resources.FirewallRules.data;
		},
		firewall() {
			return {
				disabled: true
			};
		}
	},
	data() {
		return {
			enableFirewall: false
		};
	}
};
</script>
