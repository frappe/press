<template>
	<div>
		<div class="mx-5 mt-5" v-if="!firewallName">
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
						Create Firewall
					</Button>
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
			<div v-else>
				<div class="fles">
					<div
						class="flex w-full justify-between space-x-2 pb-4 border-b bg-white px-5 py-2.5"
					>
						<header
							class="sticky top-0 z-10 flex items-center justify-between text-lg font-semibold"
						>
							{{ firewallName }}
						</header>
						<Button
							variant="outline"
							theme="gray"
							class="justify-end"
							appearance="primary"
							@click="
								$router.push({
									path: `/security/${this.server.name}/firewall/edit/${this.firewallName}`
								})
							"
						>
							Edit
						</Button>
					</div>
				</div>
				<FirewallRuleView
					:firewallName="firewallName"
					:rules="rules"
					:disableAction="true"
				/>
			</div>

			<div class="mx-2.5 border-b" />
		</div>
		<div class="mx-5 mt-15" v-if="!firewallName">
			<div class="block w-full">
				<div
					class="items-start rounded-md px-4 py-3.5 text-base md:px-5 text-gray-700 bg-gray-50"
				>
					Example:
					<div class="mt-5">
						<FirewallRuleView
							:firewallName="firewallName"
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
				url: 'press.api.security.fetch_firewall_and_rules',
				params: {
					server: this.server?.name,
					server_type: this.server?.server_type
				},
				auto: true,
				onError: this.$routeTo404PageIfNotFound,
				onSuccess: () => {
					this.firewallName = this.$resources.FirewallRules.data.firewall_name;
				}
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
		}
	},
	computed: {
		rules() {
			return this.$resources.FirewallRules.data.rules;
		},
		firewall() {
			return {
				disabled: true
			};
		}
	},
	data() {
		return {
			enableFirewall: false,
			firewallName: ''
		};
	}
};
</script>
