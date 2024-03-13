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
			<div
				v-if="serverRegion && appServerPlan && dbServerPlan"
				class="flex flex-col"
			>
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
			<div class="flex flex-col space-y-4" v-if="serverTitle && serverRegion">
				<FormControl
					type="checkbox"
					v-model="agreedToRegionConsent"
					:label="`I agree that the laws of the region selected by me shall stand applicable to me and Frappe.`"
				/>
				<ErrorMessage class="my-2" :message="$resources.createServer.error" />
				<Button
					class="w-1/2"
					variant="solid"
					:disabled="!agreedToRegionConsent"
					@click="
						$resources.createServer.submit({
							server: {
								title: serverTitle,
								cluster: serverRegion,
								app_plan: appServerPlan?.name,
								db_plan: dbServerPlan?.name
							}
						})
					"
					:loading="$resources.createServer.loading"
				>
					Create Bench
				</Button>
			</div>
		</div>
	</div>
</template>
<script>
import Header from '../components/Header.vue';
import NewObjectPlanCards from '../components/NewObjectPlanCards.vue';

export default {
	name: 'NewBench',
	components: {
		NewObjectPlanCards,
		Header
	},
	props: ['server'],
	data() {
		return {
			serverTitle: '',
			appServerPlan: '',
			dbServerPlan: '',
			serverRegion: '',
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
		}
	},
	computed: {
		options() {
			return this.$resources.options.data;
		}
	}
};
</script>
