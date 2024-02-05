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
			<div>
				<div class="flex items-center justify-between">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Select Region
					</h2>
				</div>
				<div class="mt-2">
					<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
						<button
							v-for="region in options.regions"
							:key="region.name"
							:class="[
								serverRegion === region.name
									? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
									: 'bg-white text-gray-900  ring-gray-200 hover:bg-gray-50',
								'flex w-full items-center rounded border p-3 text-left text-base text-gray-900'
							]"
							@click="
								serverRegion = region.name;
								selectedAppServerPlan = null;
								selectedDatabaseServerPlan = null;
							"
						>
							<div class="flex w-full items-center space-x-2">
								<img :src="region.image" class="h-5 w-5" />
								<span class="text-sm font-medium">
									{{ region.title }}
								</span>
								<Badge
									class="!ml-auto"
									theme="gray"
									v-if="region.beta"
									label="Beta"
								/>
							</div>
						</button>
					</div>
				</div>
			</div>
			<div>
				<div class="flex items-center justify-between">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Select App Server Plan
					</h2>
				</div>
				<div class="mt-2">
					<NewServerPlansCards
						v-model="selectedAppServerPlan"
						:plans="
							options.app_plans.filter(plan => plan.cluster === serverRegion)
						"
					/>
				</div>
			</div>
			<div>
				<div class="flex items-center justify-between">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Select Database Server Plan
					</h2>
				</div>
				<div class="mt-2">
					<NewServerPlansCards
						v-model="selectedDatabaseServerPlan"
						:plans="
							options.db_plans.filter(plan => plan.cluster === serverRegion)
						"
					/>
				</div>
			</div>
			<div>
				<div class="flex items-center justify-between">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Enter Server Title
					</h2>
				</div>
				<div class="mt-2">
					<FormControl class="w-1/2" v-model="serverTitle" />
				</div>
			</div>
			<div
				class="w-1/2"
				v-if="
					serverRegion &&
					selectedAppServerPlan &&
					selectedDatabaseServerPlan &&
					serverTitle
				"
			>
				<h2 class="text-base font-medium leading-6 text-gray-900">Summary</h2>
				<div
					class="mt-2 grid gap-x-4 gap-y-2 rounded-md border bg-gray-50 p-4 text-p-base"
					style="grid-template-columns: 3fr 4fr"
				>
					<div class="text-gray-600">Server Title:</div>
					<div class="text-gray-900">{{ serverTitle }}</div>
					<div class="text-gray-600">Region:</div>
					<div class="text-gray-900">{{ serverRegion }}</div>
					<div class="text-gray-600">App Server Plan:</div>
					<div class="text-gray-900">
						{{
							$format.userCurrency(
								$team.doc.currency == 'INR'
									? selectedAppServerPlan.price_inr
									: selectedAppServerPlan.price_usd
							)
						}}
						per month
						<div class="text-gray-600">
							{{ selectedAppServerPlan.vcpu }} vCPU
						</div>
						<div class="text-gray-600">
							{{ $format.bytes(selectedAppServerPlan.memory, 0, 2) }} GB RAM
						</div>
						<div class="text-gray-600">
							{{ $format.bytes(selectedAppServerPlan.disk, 0, 2) }} GB Disk
						</div>
					</div>
					<div class="text-gray-600">Database Server Plan:</div>
					<div class="text-gray-900">
						{{
							$format.userCurrency(
								$team.doc.currency == 'INR'
									? selectedDatabaseServerPlan.price_inr
									: selectedDatabaseServerPlan.price_usd
							)
						}}
						per month
						<div class="text-gray-600">
							{{ selectedDatabaseServerPlan.vcpu }} vCPU
						</div>
						<div class="text-gray-600">
							{{ $format.bytes(selectedDatabaseServerPlan.memory, 0, 2) }} GB
							RAM
						</div>
						<div class="text-gray-600">
							{{ $format.bytes(selectedDatabaseServerPlan.disk, 0, 2) }} GB Disk
						</div>
					</div>
					<div class="text-gray-600">Total:</div>
					<div class="text-gray-900">
						{{
							$format.userCurrency(
								$team.doc.currency == 'INR'
									? selectedAppServerPlan.price_inr +
											selectedDatabaseServerPlan.price_inr
									: selectedAppServerPlan.price_usd +
											selectedDatabaseServerPlan.price_usd
							)
						}}
						per month
						<div class="text-gray-600">
							{{
								$format.userCurrency(
									$format.pricePerDay(
										$team.doc.currency == 'INR'
											? selectedAppServerPlan.price_inr +
													selectedDatabaseServerPlan.price_inr
											: selectedAppServerPlan.price_usd +
													selectedDatabaseServerPlan.price_usd
									)
								)
							}}
							per day
						</div>
					</div>
				</div>
			</div>
			<div class="flex flex-col space-y-4">
				<FormControl
					type="checkbox"
					:disabled="
						!serverRegion ||
						!selectedAppServerPlan ||
						!selectedDatabaseServerPlan ||
						!serverTitle
					"
					v-model="agreedToRegionConsent"
					:label="`I agree that the laws of the region selected by me shall stand applicable to me and Frappe.`"
				/>
				<ErrorMessage class="my-2" :message="$resources.createServer.error" />
				<Button
					class="w-1/2"
					variant="solid"
					label="Create Servers"
					:disabled="!agreedToRegionConsent"
					@click="$resources.createServer.submit()"
				/>
			</div>
		</div>
	</div>
</template>
<script>
import Header from '../components/Header.vue';
import NewServerPlansCards from '../components/server/NewServerPlansCards.vue';
import router from '../router';

export default {
	components: {
		Header,
		NewServerPlansCards
	},
	data() {
		return {
			serverTitle: '',
			serverRegion: null,
			selectedAppServerPlan: null,
			agreedToRegionConsent: false,
			selectedDatabaseServerPlan: null
		};
	},
	resources: {
		options: {
			url: 'press.api.server.options',
			auto: true,
			initialData: {
				regions: [],
				app_plans: [],
				db_plans: []
			},
			transform(data) {
				return {
					regions: data.regions,
					app_plans: data.app_plans.map(plan => {
						return {
							...plan,
							disabled: Object.keys(this.$team.doc.billing_details).length === 0
						};
					}),
					db_plans: data.db_plans.map(plan => {
						return {
							...plan,
							disabled: Object.keys(this.$team.doc.billing_details).length === 0
						};
					})
				};
			},
			onSuccess(data) {
				this.serverRegion = data.regions[0].name;
			}
		},
		createServer() {
			return {
				url: 'press.api.server.new',
				params: {
					server: {
						title: this.serverTitle,
						cluster: this.serverRegion,
						app_plan: this.selectedAppServerPlan?.name,
						db_plan: this.selectedDatabaseServerPlan?.name
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
