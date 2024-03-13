<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs
				:items="[
					{ label: 'Servers', route: '/servers' },
					{ label: 'New Server', route: '/servers/new' }
				]"
			/>
		</Header>
	</div>

	<div class="mx-auto max-w-4xl">
		<div v-if="options" class="space-y-12 pb-[50vh] pt-12">
			<div class="flex flex-col">
				<h2 class="text-sm font-medium leading-6 text-gray-900">
					Choose Server Type
				</h2>
				<div class="mt-2 w-full space-y-2">
					<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
						<button
							v-for="c in options?.server_types"
							:key="c.name"
							@click="serverType = c.name"
							:class="[
								serverType === c.name
									? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
									: 'border-gray-400 bg-white text-gray-900 ring-gray-200 hover:bg-gray-50',
								'flex w-full items-center rounded border p-3 text-left text-base text-gray-900'
							]"
						>
							<div class="flex w-full items-center justify-between space-x-2">
								<span class="text-sm font-medium">
									{{ c.title }}
								</span>
								<Tooltip :text="c.description">
									<i-lucide-info class="h-4 w-4 text-gray-500" />
								</Tooltip>
							</div>
						</button>
					</div>
				</div>
			</div>
			<div v-if="serverType" class="flex flex-col">
				<h2 class="text-sm font-medium leading-6 text-gray-900">
					Enter Server Name
				</h2>
				<div class="mt-2">
					<FormControl
						v-model="serverTitle"
						type="text"
						class="block w-1/2 rounded-md border-gray-300 shadow-sm focus:border-gray-900 focus:ring-gray-900 sm:text-sm"
					/>
				</div>
			</div>
			<div v-if="serverType === 'dedicated'" class="space-y-12">
				<div class="flex flex-col" v-if="options?.regions.length">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Select Region
					</h2>
					<div class="mt-2 w-full space-y-2">
						<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
							<button
								v-for="c in options?.regions"
								:key="c.name"
								@click="serverRegion = c.name"
								:class="[
									serverRegion === c.name
										? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
										: 'border-gray-400 bg-white text-gray-900 ring-gray-200 hover:bg-gray-50',
									'flex w-full items-center rounded border p-3 text-left text-base text-gray-900'
								]"
							>
								<div class="flex w-full items-center space-x-2">
									<img :src="c.image" class="h-5 w-5" />
									<span class="text-sm font-medium">
										{{ c.title }}
									</span>
								</div>
							</button>
						</div>
					</div>
				</div>
				<div v-if="serverRegion">
					<div class="flex flex-col" v-if="options?.app_plans.length">
						<h2 class="text-sm font-medium leading-6 text-gray-900">
							Select Application Server Plan
						</h2>
						<div class="mt-2 w-full space-y-2">
							<NewObjectPlanCards
								v-model="appServerPlan"
								:plans="options.app_plans"
							/>
						</div>
					</div>
				</div>
				<div v-if="serverRegion">
					<div class="flex flex-col" v-if="options?.db_plans.length">
						<h2 class="text-sm font-medium leading-6 text-gray-900">
							Select Database Server Plan
						</h2>
						<div class="mt-2 w-full space-y-2">
							<NewObjectPlanCards
								v-model="dbServerPlan"
								:plans="options.db_plans"
							/>
						</div>
					</div>
				</div>
			</div>
			<div v-else-if="serverType === 'hybrid'" class="space-y-12">
				<div class="flex flex-col space-y-2">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						App Server IP Addresses
					</h2>
					<div class="flex space-x-3">
						<FormControl v-model="appPublicIP" label="Public IP" type="text" />
						<FormControl
							v-model="appPrivateIP"
							label="Private IP"
							type="text"
						/>
					</div>
				</div>
				<div class="flex flex-col space-y-2">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Database Server IP Addresses
					</h2>
					<div class="flex space-x-3">
						<FormControl v-model="dbPublicIP" label="Public IP" type="text" />
						<FormControl v-model="dbPrivateIP" label="Private IP" type="text" />
					</div>
				</div>
				<div class="flex flex-col space-y-2">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Add SSH Key
					</h2>
					<span class="w-1/2 text-xs text-gray-600">
						Add this SSH Key to
						<span class="font-mono">~/.ssh/authorized_keys</span>
						file on Application and Database server</span
					>
					<ClickToCopy
						class="w-1/2"
						:textContent="$resources.hybridOptions.data.ssh_key"
					/>
				</div>
			</div>
			<div
				class="flex flex-col space-y-4"
				v-if="
					serverTitle &&
					(serverRegion ||
						(appPublicIP && appPrivateIP && dbPublicIP && dbPrivateIP))
				"
			>
				<FormControl
					type="checkbox"
					v-model="agreedToRegionConsent"
					:label="`I agree that the laws of the region selected by me shall stand applicable to me and Frappe.`"
				/>
				<ErrorMessage
					class="my-2"
					:message="
						$resources.createServer.error || $resources.createHybridServer.error
					"
				/>
				<Button
					class="w-1/2"
					variant="solid"
					:disabled="!agreedToRegionConsent"
					@click="
						serverType === 'dedicated'
							? $resources.createServer.submit({
									server: {
										title: serverTitle,
										cluster: serverRegion,
										app_plan: appServerPlan?.name,
										db_plan: dbServerPlan?.name
									}
							  })
							: $resources.createHybridServer.submit({
									server: {
										title: serverTitle,
										app_public_ip: appPublicIP,
										app_private_ip: appPrivateIP,
										db_public_ip: dbPublicIP,
										db_private_ip: dbPrivateIP
									}
							  })
					"
					:loading="$resources.createServer.loading"
				>
					Create Server
				</Button>
			</div>
		</div>
	</div>
</template>
<script>
import Header from '../components/Header.vue';
import NewObjectPlanCards from '../components/NewObjectPlanCards.vue';
import ClickToCopy from '../../src/components/ClickToCopyField.vue';

export default {
	components: {
		NewObjectPlanCards,
		ClickToCopy,
		Header
	},
	props: ['server'],
	data() {
		return {
			serverTitle: '',
			appServerPlan: '',
			dbServerPlan: '',
			serverRegion: '',
			serverType: '',
			appPublicIP: '',
			appPrivateIP: '',
			dbPublicIP: '',
			dbPrivateIP: '',
			agreedToRegionConsent: false
		};
	},
	resources: {
		options() {
			return {
				url: 'press.api.server.options',
				auto: true,
				transform(data) {
					return {
						server_types: [
							{
								name: 'dedicated',
								title: 'Dedicated Server',
								description:
									'A pair of dedicated servers managed and owned by frappe'
							},
							{
								name: 'hybrid',
								title: 'Hybrid Server',
								description:
									'A pair of dedicated servers managed by frappe and owned/provisioned by you'
							}
						],
						regions: data.regions,
						app_plans: data.app_plans.map(plan => {
							return {
								...plan,
								features: [
									{
										label: 'vCPUs',
										value: plan.vcpu
									},
									{
										label: 'Memory',
										value: this.$format.bytes(plan.memory, 0, 2)
									},
									{
										label: 'Disk',
										value: this.$format.bytes(plan.disk, 0, 2)
									},
									{
										label: 'Instance Type',
										value: plan.instance_type
									}
								],
								disabled:
									Object.keys(this.$team.doc.billing_details).length === 0
							};
						}),
						db_plans: data.db_plans.map(plan => {
							return {
								...plan,
								features: [
									{
										label: 'vCPUs',
										value: plan.vcpu
									},
									{
										label: 'Memory',
										value: this.$format.bytes(plan.memory, 0, 2)
									},
									{
										label: 'Disk',
										value: this.$format.bytes(plan.disk, 0, 2)
									},
									{
										label: 'Instance Type',
										value: plan.instance_type
									}
								],
								disabled:
									Object.keys(this.$team.doc.billing_details).length === 0
							};
						})
					};
				}
			};
		},
		hybridOptions() {
			return {
				url: 'press.api.selfhosted.options_for_new',
				auto: true
			};
		},
		createServer() {
			return {
				url: 'press.api.server.new',
				validate({ server }) {
					if (!server.title) {
						return 'Server name is required';
					} else if (!server.cluster) {
						return 'Please select a region';
					} else if (!server.app_plan) {
						return 'Please select an App Server Plan';
					} else if (!server.db_plan) {
						return 'Please select a Database Server Plan';
					}
				},
				onSuccess(server) {
					router.push({
						name: 'Server Detail Plays',
						params: { name: server.server }
					});
				}
			};
		},
		createHybridServer() {
			return {
				url: 'press.api.selfhosted.new',
				validate() {
					if (!this.serverTitle) {
						return 'Server name is required';
					} else if (
						!this.appPublicIP ||
						!this.dbPublicIP ||
						!this.appPrivateIP ||
						!this.dbPrivateIP
					) {
						return 'Please fill all the IP addresses';
					} else if (this.dbPublicIP === this.appPublicIP) {
						return "Please don't use the same server as Application and Database servers";
					} else if (!this.agreedToRegionConsent) {
						return 'Please agree to the region consent';
					}
				}
			};
		}
	},
	computed: {
		options() {
			return this.$resources.options.data;
		}
	}
};
</script>
