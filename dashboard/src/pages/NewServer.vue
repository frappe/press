<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs
				:items="[
					{ label: 'Servers', route: '/servers' },
					{ label: 'New Server', route: '/servers/new' },
				]"
			/>
		</Header>
	</div>

	<div
		v-if="!$team.doc?.is_desk_user && !$session.hasServerCreationAccess"
		class="mx-auto mt-60 w-fit rounded border border-dashed px-12 py-8 text-center text-gray-600"
	>
		<lucide-alert-triangle class="mx-auto mb-4 h-6 w-6 text-red-600" />
		<ErrorMessage message="You aren't permitted to create new servers" />
	</div>

	<div v-else-if="serverEnabled" class="mx-auto max-w-2xl px-5">
		<div v-if="options" class="space-y-8 pb-[50vh] pt-12">
			<div class="flex flex-col">
				<h2 class="text-sm font-medium leading-6 text-gray-900">
					Choose Server Type
				</h2>
				<div class="mt-2 w-full space-y-2">
					<div class="grid grid-cols-2 gap-3">
						<button
							v-for="c in options?.server_types"
							:key="c.name"
							@click="serverType = c.name"
							:class="[
								serverType === c.name
									? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
									: 'border-gray-400 bg-white text-gray-900 ring-gray-200 hover:bg-gray-50',
								'flex w-full items-center rounded border p-3 text-left text-base text-gray-900',
							]"
						>
							<div class="flex w-full items-center justify-between space-x-2">
								<span class="text-sm font-medium">
									{{ c.title }}
								</span>
								<Tooltip :text="c.description">
									<lucide-info class="h-4 w-4 text-gray-500" />
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
						class="block rounded-md border-gray-300 shadow-sm focus:border-gray-900 focus:ring-gray-900 sm:text-sm"
					/>
				</div>
			</div>
			<div v-if="serverType === 'dedicated'" class="space-y-8">
				<!-- Chose Region -->
				<div class="flex flex-col" v-if="options?.regions_data">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Select Region
					</h2>
					<div class="mt-2 w-full space-y-2">
						<div class="grid grid-cols-2 gap-3">
							<button
								v-for="r in Object.keys(options?.regions_data ?? {})"
								:key="r"
								@click="serverRegion = r"
								:class="[
									serverRegion === r
										? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
										: 'border-gray-400 bg-white text-gray-900 ring-gray-200 hover:bg-gray-50',
									'flex w-full items-center rounded border p-3 text-left text-base text-gray-900',
								]"
							>
								<div class="flex w-full items-center justify-between">
									<div class="flex w-full items-center space-x-2">
										<img :src="options.regions_data[r].image" class="h-5 w-5" />
										<span class="text-sm font-medium">
											{{ r }}
										</span>
									</div>
								</div>
							</button>
						</div>
					</div>
				</div>
				<!-- Choose Server Provider -->
				<div class="flex flex-col" v-if="serverRegion && providers">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Select Provider
					</h2>
					<div class="mt-2 w-full space-y-2">
						<div class="grid grid-cols-2 gap-3">
							<button
								v-for="provider in Object.keys(providers).sort((a, b) =>
									a.localeCompare(b),
								)"
								:key="provider"
								@click="serverProvider = provider"
								:class="[
									serverProvider === provider
										? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
										: 'border-gray-400 bg-white text-gray-900 ring-gray-200 hover:bg-gray-50',
									'flex w-full items-center rounded border p-3 text-left text-base text-gray-900',
								]"
							>
								<div class="flex w-full items-center justify-between">
									<div class="flex w-full items-center space-x-2">
										<img
											:src="providers[provider].provider_image"
											class="h-5 w-5"
										/>
										<span class="text-sm font-medium">
											{{ providers[provider].title }}
										</span>
									</div>
									<Badge
										v-if="providers[provider].beta"
										:label="providers[provider].beta ? 'Beta' : ''"
										theme="orange"
										variant="outline"
										size="md"
									/>
								</div>
							</button>
						</div>
					</div>
				</div>
				<!-- Chose Plan Type -->
				<!-- Choose Service Type (Premium/Standard) -->
				<div
					v-if="
						serverRegion &&
						serverProvider &&
						options.app_premium_plans.length > 0
					"
					class="flex flex-col"
				>
					<div class="flex items-center justify-between">
						<h2 class="text-sm font-medium leading-6 text-gray-900">
							Service Type
						</h2>
						<div>
							<Button
								link="https://frappecloud.com/pricing#dedicated"
								variant="ghost"
							>
								<template #prefix>
									<lucide-help-circle class="h-4 w-4 text-gray-700" />
								</template>
								Help
							</Button>
						</div>
					</div>
					<div class="mt-2 w-full space-y-2">
						<div class="grid grid-cols-2 gap-3">
							<button
								v-for="c in [
									{
										name: 'Standard',
										description: 'Includes standard support and SLAs',
									},
									{
										name: 'Premium',
										description: 'Includes enterprise support and SLAs',
									},
								]"
								:key="c.name"
								@click="serviceType = c.name"
								:class="[
									serviceType === c.name
										? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
										: 'border-gray-400 bg-white text-gray-900 ring-gray-200 hover:bg-gray-50',
									'flex w-full items-center rounded border p-3 text-left text-base text-gray-900',
								]"
							>
								<div class="flex w-full items-center justify-between space-x-2">
									<span class="text-sm font-medium">
										{{ c.name }}
									</span>
									<Tooltip :text="c.description">
										<lucide-info class="h-4 w-4 text-gray-500" />
									</Tooltip>
								</div>
							</button>
						</div>
					</div>
				</div>
				<!-- Choose App Server Plan -->
				<div v-if="serverRegion && serverProvider && selectedCluster">
					<div
						class="flex flex-col space-y-4"
						v-if="availableAppPlanTypes.length"
					>
						<h2 class="text-sm font-medium leading-6 text-gray-900">
							Select Application Server Plan
						</h2>

						<!-- App Server Plan Type Selection -->
						<div
							class="w-full space-y-2"
							v-if="availableAppPlanTypes.length > 1"
						>
							<div class="grid grid-cols-2 gap-3">
								<button
									v-for="planType in availableAppPlanTypes"
									:key="planType.name"
									@click="appServerPlanType = planType.name"
									:class="[
										appServerPlanType === planType.name
											? 'border-gray-900 ring-1 ring-gray-900'
											: 'border-gray-300',
										'flex w-full flex-col overflow-hidden rounded border text-left hover:bg-gray-50',
									]"
								>
									<div class="w-full p-3">
										<div class="flex items-center justify-between">
											<div class="flex w-full items-center">
												<span
													class="truncate text-lg font-medium text-gray-900"
												>
													{{ planType.title }}
												</span>
											</div>
										</div>
										<div
											class="mt-1 text-sm text-gray-600"
											v-if="planType.description"
										>
											{{ planType.description }}
										</div>
									</div>
								</button>
							</div>
						</div>

						<!-- Single Plan Type Message -->
						<div
							v-else-if="availableAppPlanTypes.length === 1"
							class="flex flex-col rounded border border-gray-300 p-3 gap-2"
						>
							<p class="text-base text-gray-900">
								<span class="font-medium">{{
									availableAppPlanTypes[0].title
								}}</span>
								machines are available.
							</p>

							<p class="text-base text-gray-600">
								{{ availableAppPlanTypes[0].description }}
							</p>
						</div>

						<!-- App Server Plans -->
						<div v-if="appServerPlanType" class="mt-2 space-y-2">
							<ServerPlansCards
								v-model="appServerPlan"
								:plans="filteredAppPlans"
							/>
						</div>
					</div>
				</div>
				<!-- Choose Database Server Plan -->
				<div v-if="serverRegion && serverProvider && selectedCluster">
					<div
						class="flex flex-col space-y-4"
						v-if="availableDbPlanTypes.length"
					>
						<h2 class="text-sm font-medium leading-6 text-gray-900">
							Select Database Server Plan
						</h2>

						<!-- DB Server Plan Type Selection -->
						<div class="w-full" v-if="availableDbPlanTypes.length > 1">
							<div class="grid grid-cols-2 gap-3">
								<button
									v-for="planType in availableDbPlanTypes"
									:key="planType.name"
									@click="dbServerPlanType = planType.name"
									:class="[
										dbServerPlanType === planType.name
											? 'border-gray-900 ring-1 ring-gray-900'
											: 'border-gray-300',
										'flex w-full flex-col overflow-hidden rounded border text-left hover:bg-gray-50',
									]"
								>
									<div class="w-full p-3">
										<div class="flex items-center justify-between">
											<div class="flex w-full items-center">
												<span
													class="truncate text-lg font-medium text-gray-900"
												>
													{{ planType.title }}
												</span>
											</div>
										</div>
										<div
											class="mt-1 text-sm text-gray-600"
											v-if="planType.description"
										>
											{{ planType.description }}
										</div>
									</div>
								</button>
							</div>
						</div>

						<!-- Single Plan Type Message -->
						<div
							v-else-if="availableDbPlanTypes.length === 1"
							class="flex flex-col rounded border border-gray-300 p-3 gap-2"
						>
							<p class="text-base text-gray-900">
								<span class="font-medium">{{
									availableDbPlanTypes[0].title
								}}</span>
								machines are available.
							</p>

							<p class="text-base text-gray-600">
								{{ availableDbPlanTypes[0].description }}
							</p>
						</div>

						<!-- DB Server Plans -->
						<div v-if="dbServerPlanType" class="mt-2 w-full space-y-2">
							<ServerPlansCards
								v-model="dbServerPlan"
								:plans="filteredDbPlans"
							/>
						</div>
					</div>
				</div>
			</div>
			<div v-else-if="serverType === 'hybrid'" class="space-y-8">
				<div class="flex flex-col space-y-2">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						App Server IP Addresses
					</h2>
					<div class="flex space-x-3">
						<FormControl
							class="w-full"
							v-model="appPublicIP"
							label="Public IP"
							type="text"
						/>
						<FormControl
							class="w-full"
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
						<FormControl
							class="w-full"
							v-model="dbPublicIP"
							label="Public IP"
							type="text"
						/>
						<FormControl
							class="w-full"
							v-model="dbPrivateIP"
							label="Private IP"
							type="text"
						/>
					</div>
				</div>
				<div class="flex flex-col space-y-2">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Add SSH Key
					</h2>
					<span class="text-xs text-gray-600">
						Add this SSH Key to
						<span class="font-mono">~/.ssh/authorized_keys</span>
						file on Application and Database server</span
					>
					<ClickToCopy
						:textContent="$resources.hybridOptions.data?.ssh_key || ''"
					/>
				</div>
			</div>
			<div class="flex flex-col space-y-3" v-if="showAutoAddStorageOption">
				<h2 class="text-base font-medium leading-6 text-gray-900">
					Auto Add-on Storage
				</h2>
				<div class="my-4 rounded border bg-gray-50 p-2 prose-sm prose">
					This feature will automatically increases the storage as it reaches
					over <b>90%</b> of its capacity.

					<br /><br />
					With this feature disabled, disk capacity
					<strong>will not increase automatically</strong> in the event your
					server approaches or reaches its storage limit.

					<br /><br />
					<strong>Note :</strong>

					<ul>
						<li v-if="this.storagePlanRate">
							• You will be charged at the rate of
							<b>{{ this.$format.userCurrency(this.storagePlanRate) }}/mo</b>
							for each additional GB of storage.
						</li>

						<li>
							• Disabling this feature may result in
							<strong>service degradation or downtime</strong> if storage is
							exhausted.
						</li>

						<li>
							• Storage can auto increase only once in <strong>6 hours</strong>.
						</li>
					</ul>
				</div>
				<div>
					<FormControl
						type="checkbox"
						v-model="enableAutoAddStorage"
						label="Enable Auto Add-on Storage for Application and Database Server"
					/>
				</div>
			</div>

			<Summary
				:options="summaryOptions"
				v-if="
					serverTitle &&
					((serverRegion && dbServerPlan && appServerPlan) ||
						(appPublicIP && appPrivateIP && dbPublicIP && dbPrivateIP))
				"
			/>
			<div
				class="flex flex-col space-y-4"
				v-if="
					serverTitle &&
					((serverRegion && dbServerPlan && appServerPlan) ||
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
					variant="solid"
					:disabled="!agreedToRegionConsent"
					@click="
						serverType === 'dedicated'
							? $resources.createServer.submit({
									server: {
										title: serverTitle,
										cluster: selectedCluster,
										app_plan: appServerPlan?.name,
										db_plan: dbServerPlan?.name,
										auto_increase_storage: enableAutoAddStorage,
									},
								})
							: $resources.createHybridServer.submit({
									server: {
										title: serverTitle,
										app_public_ip: appPublicIP,
										app_private_ip: appPrivateIP,
										db_public_ip: dbPublicIP,
										db_private_ip: dbPrivateIP,
										plan: $resources.hybridOptions.data?.plans?.[0],
									},
								})
					"
					:loading="
						$resources.createServer.loading ||
						$resources.createHybridServer.loading
					"
				>
					{{ serverType === 'hybrid' ? 'Add Hybrid Server' : 'Create Server' }}
				</Button>
			</div>
		</div>
	</div>
	<div
		v-else
		class="mx-auto mt-60 w-fit rounded border-2 border-dashed px-12 py-8 text-center text-gray-600"
	>
		<LucideServer class="mx-auto mb-4 h-8 w-8" />
		<p>Server feature isn't enabled for your account.</p>
		<p>You need to have $200 worth of credits to enable this feature.</p>
		<p>
			Please add it from
			<router-link class="underline" :to="{ name: 'BillingOverview' }"
				>here</router-link
			>.
		</p>
		<p>
			Or you can
			<a
				class="underline"
				href="https://frappecloud.com/support"
				target="_blank"
				>contact support</a
			>
			to enable it.
		</p>
	</div>
</template>
<script>
import LucideServer from '~icons/lucide/server-off';
import Header from '../components/Header.vue';
import Summary from '../components/Summary.vue';
import ServerPlansCards from '../components/server/ServerPlansCards.vue';
import ClickToCopy from '../components/ClickToCopyField.vue';
import { DashboardError } from '../utils/error';

export default {
	components: {
		ServerPlansCards,
		LucideServer,
		ClickToCopy,
		Summary,
		Header,
	},
	props: ['server'],
	data() {
		return {
			serverTitle: '',
			appServerPlan: '',
			dbServerPlan: '',
			serverRegion: '',
			serverProvider: '',
			serverType: '',
			appPublicIP: '',
			appPrivateIP: '',
			dbPublicIP: '',
			dbPrivateIP: '',
			serviceType: 'Standard',
			appServerPlanType: '',
			dbServerPlanType: '',
			serverEnabled: true,
			enableAutoAddStorage: false,
			agreedToRegionConsent: false,
		};
	},
	watch: {
		serverRegion() {
			if (Object.keys(this.providers).length > 0) {
				this.serverProvider = Object.keys(this.providers).sort((a, b) =>
					a.localeCompare(b),
				)[0];
			} else {
				this.serverProvider = '';
			}
			this.appServerPlanType = '';
			this.dbServerPlanType = '';
			this.appServerPlan = '';
			this.dbServerPlan = '';
		},
		serverType() {
			this.appServerPlan = '';
			this.dbServerPlan = '';
			this.serverRegion = '';
			this.appServerPlanType = '';
			this.dbServerPlanType = '';
			this.appPublicIP = '';
			this.appPrivateIP = '';
			this.dbPublicIP = '';
			this.dbPrivateIP = '';
		},
		serviceType() {
			this.appServerPlan = '';
			this.dbServerPlan = '';
		},
		selectedCluster() {
			this.appServerPlanType = '';
			this.dbServerPlanType = '';
			this.appServerPlan = '';
			this.dbServerPlan = '';
		},
		availableAppPlanTypes() {
			// Auto-select if only one plan type is available
			if (this.availableAppPlanTypes.length === 1) {
				this.appServerPlanType = this.availableAppPlanTypes[0].name;
			} else if (this.availableAppPlanTypes.length === 0) {
				this.appServerPlanType = '';
			}
		},
		availableDbPlanTypes() {
			// Auto-select if only one plan type is available
			if (this.availableDbPlanTypes.length === 1) {
				this.dbServerPlanType = this.availableDbPlanTypes[0].name;
			} else if (this.availableDbPlanTypes.length === 0) {
				this.dbServerPlanType = '';
			}
		},
		appServerPlanType() {
			this.appServerPlan = '';
		},
		dbServerPlanType() {
			this.dbServerPlan = '';
		},
	},
	resources: {
		options() {
			return {
				url: 'press.api.server.options',
				auto: true,
				transform(data) {
					const fillPlanType = (plans) => {
						return plans.map((plan) => ({
							...plan,
							...(data.default_plan_type &&
								!plan.plan_type && { plan_type: data.default_plan_type }),
						}));
					};

					return {
						server_types: [
							{
								name: 'dedicated',
								title: 'Dedicated Server',
								description:
									'A pair of dedicated servers managed and owned by frappe',
							},
							{
								name: 'hybrid',
								title: 'Hybrid Server',
								description:
									'A pair of dedicated servers managed by frappe and owned/provisioned by you',
							},
						],
						regions: data.regions,
						regions_data: data.regions_data,
						plan_types: data.plan_types,
						default_plan_type: data.default_plan_type,
						app_plans: fillPlanType(
							data.app_plans.filter((p) => p.premium == 0),
						),
						db_plans: fillPlanType(data.db_plans.filter((p) => p.premium == 0)),
						app_premium_plans: fillPlanType(
							data.app_plans.filter((p) => p.premium == 1),
						),
						db_premium_plans: fillPlanType(
							data.db_plans.filter((p) => p.premium == 1),
						),
						storage_plan: data.storage_plan,
					};
				},
				onError(error) {
					if (
						error &&
						error.messages &&
						error.messages.includes(
							'Servers feature is not yet enabled on your account',
						)
					) {
						this.serverEnabled = false;
					} else {
						console.error(error);
					}
				},
			};
		},
		hybridOptions() {
			return {
				url: 'press.api.selfhosted.options_for_new',
				auto: true,
			};
		},
		createServer() {
			return {
				url: 'press.api.server.new',
				validate({ server }) {
					if (!server.title) {
						throw new DashboardError('Server name is required');
					} else if (!server.cluster) {
						throw new DashboardError('Please select a region');
					} else if (!server.app_plan) {
						throw new DashboardError('Please select an App Server Plan');
					} else if (!server.db_plan) {
						throw new DashboardError('Please select a Database Server Plan');
					} else if (Object.keys(this.$team.doc.billing_details).length === 0) {
						throw new DashboardError(
							"You don't have billing details added. Please add billing details from settings to continue.",
						);
					} else if (
						this.$team.doc.servers_enabled == 0 &&
						((this.$team.doc.currency == 'USD' &&
							this.$team.doc.balance < 200) ||
							(this.$team.doc.currency == 'INR' &&
								this.$team.doc.balance < 16000))
					) {
						throw new DashboardError(
							'You need to have $200 worth of credits to create a server.',
						);
					}
				},
				onSuccess(server) {
					this.$router.push({
						name: 'Server Detail Plays',
						params: { name: server.server },
					});
				},
			};
		},
		createHybridServer() {
			return {
				url: 'press.api.selfhosted.create_and_verify_selfhosted',
				validate() {
					if (!this.serverTitle) {
						throw new DashboardError('Server name is required');
					} else if (
						!this.appPublicIP ||
						!this.dbPublicIP ||
						!this.appPrivateIP ||
						!this.dbPrivateIP
					) {
						throw new DashboardError('Please fill all the IP addresses');
					} else if (this.validateIP(this.appPublicIP)) {
						throw new DashboardError(
							'Please enter a valid Application Public IP',
						);
					} else if (this.validateIP(this.appPrivateIP)) {
						throw new DashboardError(
							'Please enter a valid Application Private IP',
						);
					} else if (this.validateIP(this.dbPublicIP)) {
						throw new DashboardError('Please enter a valid Database Public IP');
					} else if (this.validateIP(this.dbPrivateIP)) {
						throw new DashboardError(
							'Please enter a valid Database Private IP',
						);
						//} else if (this.dbPublicIP === this.appPublicIP) {
						//throw new DashboardError(
						//"Please don't use the same server as Application and Database servers",
						//);
					} else if (!this.agreedToRegionConsent) {
						throw new DashboardError('Please agree to the region consent');
					}
				},
				onSuccess(server) {
					this.$router.push({
						name: 'Server Detail Plays',
						params: { name: server },
					});
				},
			};
		},
	},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		providers() {
			if (!this.serverRegion) return {};
			if (!this.options?.regions_data) return {};
			return this.options.regions_data[this.serverRegion]?.providers || {};
		},
		selectedCluster() {
			if (!this.serverRegion) return null;
			if (!this.options?.regions_data) return null;
			if (!this.serverProvider) return null;
			return this.options.regions_data[this.serverRegion]?.providers[
				this.serverProvider
			]?.cluster_name;
		},
		availableAppPlanTypes() {
			if (!this.selectedCluster || !this.options?.plan_types) return [];

			const planTypes = [];
			const planTypeData = this.options.plan_types;

			for (const [key, planType] of Object.entries(planTypeData)) {
				const hasAppPlans = this.options.app_plans.some(
					(plan) =>
						plan.cluster === this.selectedCluster && plan.plan_type === key,
				);

				if (hasAppPlans) {
					planTypes.push({
						name: key,
						title: planType.title,
						description: planType.description,
						order: planType.order_in_list || 999,
					});
				}
			}

			return planTypes.sort((a, b) => a.order - b.order);
		},
		availableDbPlanTypes() {
			if (!this.selectedCluster || !this.options?.plan_types) return [];

			const planTypes = [];
			const planTypeData = this.options.plan_types;

			for (const [key, planType] of Object.entries(planTypeData)) {
				const hasDbPlans = this.options.db_plans.some(
					(plan) =>
						plan.cluster === this.selectedCluster && plan.plan_type === key,
				);

				if (hasDbPlans) {
					planTypes.push({
						name: key,
						title: planType.title,
						description: planType.description,
						order: planType.order_in_list || 999,
					});
				}
			}

			return planTypes.sort((a, b) => a.order - b.order);
		},
		filteredAppPlans() {
			if (
				!this.selectedCluster ||
				!this.appServerPlanType ||
				!this.options?.app_plans
			)
				return [];

			return (
				this.serviceType === 'Standard'
					? this.options.app_plans
					: this.options.app_premium_plans
			).filter((p) => {
				const isARMSupportedCluster =
					p.cluster === 'Mumbai' || p.cluster === 'Frankfurt';
				return (
					p.cluster === this.selectedCluster &&
					p.plan_type === this.appServerPlanType &&
					(!isARMSupportedCluster || p.platform === 'arm64')
				);
			});
		},
		filteredDbPlans() {
			if (
				!this.selectedCluster ||
				!this.dbServerPlanType ||
				!this.options?.db_plans
			)
				return [];

			return (
				this.serviceType === 'Standard'
					? this.options.db_plans
					: this.options.db_premium_plans
			).filter((p) => {
				const isARMSupportedCluster =
					p.cluster === 'Mumbai' || p.cluster === 'Frankfurt';
				return (
					p.cluster === this.selectedCluster &&
					p.plan_type === this.dbServerPlanType &&
					(!isARMSupportedCluster || p.platform === 'arm64')
				);
			});
		},
		showAutoAddStorageOption() {
			return (
				this.serverType === 'dedicated' &&
				this.serverRegion &&
				this.serverProvider &&
				this.options.regions_data[this.serverRegion]?.providers[
					this.serverProvider
				]?.has_add_on_storage_support
			);
		},
		selectedRegionInfo() {
			return this.options?.regions.find((r) => r.name === this.serverRegion);
		},
		_totalPerMonth() {
			let currencyField =
				this.$team.doc.currency == 'INR' ? 'price_inr' : 'price_usd';
			if (this.serverType === 'dedicated') {
				if (!this.appServerPlan || !this.dbServerPlan) return 0;
				return (
					this.appServerPlan[currencyField] + this.dbServerPlan[currencyField]
				);
			} else if (this.serverType === 'hybrid') {
				const hybridPlan = this.$resources.hybridOptions?.data?.plans?.[0];
				if (!hybridPlan) return 0;
				return hybridPlan[currencyField] * 2;
			}
			return 0;
		},
		totalPerMonth() {
			return this.$format.userCurrency(this._totalPerMonth);
		},
		totalPerDay() {
			return this.$format.userCurrency(
				this.$format.pricePerDay(this._totalPerMonth),
			);
		},
		summaryOptions() {
			return [
				{
					label: 'Server Name',
					value: this.serverTitle,
				},
				{
					label: 'Region',
					value: this.serverRegion,
					condition: () => this.serverType === 'dedicated',
				},
				{
					label: 'App Server Plan',
					value: this.$format.planTitle(this.appServerPlan) + ' per month',
					condition: () => this.serverType === 'dedicated',
				},
				{
					label: 'DB Server Plan',
					value: this.$format.planTitle(this.dbServerPlan) + ' per month',
					condition: () => this.serverType === 'dedicated',
				},
				{
					label: 'App Public IP',
					value: this.appPublicIP,
					condition: () => this.serverType === 'hybrid',
				},
				{
					label: 'App Private IP',
					value: this.appPrivateIP,
					condition: () => this.serverType === 'hybrid',
				},
				{
					label: 'DB Public IP',
					value: this.dbPublicIP,
					condition: () => this.serverType === 'hybrid',
				},
				{
					label: 'DB Private IP',
					value: this.dbPrivateIP,
					condition: () => this.serverType === 'hybrid',
				},
				{
					label: 'Plan',
					value: `${this.$format.planTitle(
						this.$resources.hybridOptions?.data?.plans[0],
					)} per month`,
					condition: () =>
						this.serverType === 'hybrid' &&
						this.$resources.hybridOptions?.data?.plans[0],
				},
				{
					label: 'Total',
					value: `${this.totalPerMonth} per month <div class="text-gray-600"> ${this.totalPerDay} per day</div>`,
					condition: () => this._totalPerMonth,
				},
			];
		},
		storagePlanRate() {
			if (!this.$team?.doc?.currency) return -1;
			try {
				let priceField =
					this.$team.doc.currency === 'INR' ? 'price_inr' : 'price_usd';
				console.log(this.options);
				return this.options?.storage_plan?.[priceField] || 0;
			} catch (error) {
				return -1;
			}
		},
	},
	methods: {
		validateIP(ip) {
			return !ip.match(
				/^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
			);
		},
	},
};
</script>
