<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs
				:items="
					server
						? [
								{
									label: 'Servers',
									route: '/servers'
								},
								{
									label: server,
									route: `/servers/${server}`
								},
								{
									label: 'New Bench',
									route: '/benches/new'
								}
						  ]
						: [
								{ label: 'Benches', route: '/benches' },
								{ label: 'New Bench', route: '/benches/new' }
						  ]
				"
			/>
		</Header>
	</div>

	<div class="mx-auto max-w-2xl px-5">
		<div v-if="options" class="space-y-12 pb-[50vh] pt-12">
			<div>
				<div class="flex items-center justify-between">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Select Frappe Framework Version
					</h2>
				</div>
				<div class="mt-2">
					<div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
						<button
							v-for="version in options.versions"
							:key="version.name"
							:class="[
								benchVersion === version.name
									? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
									: 'bg-white text-gray-900  hover:bg-gray-50',
								'flex cursor-pointer items-center justify-between rounded border border-gray-400 p-3 text-sm focus:outline-none'
							]"
							@click="benchVersion = version.name"
						>
							<span class="font-medium">{{ version.name }} </span>
							<span class="ml-1 text-gray-600">
								{{ version.status }}
							</span>
						</button>
					</div>
				</div>
			</div>
			<div
				class="flex flex-col"
				v-if="options?.clusters.length && benchVersion && !server"
			>
				<h2 class="text-sm font-medium leading-6 text-gray-900">
					Select Region
				</h2>
				<div class="mt-2 w-full space-y-2">
					<div class="grid grid-cols-2 gap-3">
						<button
							v-for="c in options?.clusters"
							:key="c.name"
							@click="benchRegion = c.name"
							:class="[
								benchRegion === c.name
									? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
									: 'border-gray-400 bg-white text-gray-900 ring-gray-200 hover:bg-gray-50',
								'flex w-full items-center rounded border p-3 text-left text-base text-gray-900'
							]"
						>
							<div class="flex w-full items-center justify-between">
								<div class="flex w-full items-center space-x-2">
									<img :src="c.image" class="h-5 w-5" />
									<span class="text-sm font-medium">
										{{ c.title }}
									</span>
								</div>
								<Badge v-if="c.beta" :label="c.beta ? 'Beta' : ''" />
							</div>
						</button>
					</div>
				</div>
			</div>
			<div v-if="benchVersion && (benchRegion || server)" class="flex flex-col">
				<h2 class="text-sm font-medium leading-6 text-gray-900">
					Enter Bench Title
				</h2>
				<div class="mt-2">
					<FormControl v-model="benchTitle" type="text" />
				</div>
			</div>
			<Summary
				v-if="benchVersion && (benchRegion || server) && benchTitle"
				:options="summaryOptions"
			/>
			<div
				class="flex flex-col space-y-4"
				v-if="benchVersion && (benchRegion || server) && benchTitle"
			>
				<FormControl
					type="checkbox"
					v-model="agreedToRegionConsent"
					:label="`I agree that the laws of the region selected by me shall stand applicable to me and Frappe.`"
				/>
				<ErrorMessage class="my-2" :message="$resources.createBench.error" />
				<Button
					variant="solid"
					:disabled="!agreedToRegionConsent"
					@click="
						$resources.createBench.submit({
							bench: {
								title: benchTitle,
								version: benchVersion,
								cluster: benchRegion,
								saas_app: null,
								apps: [
									// some wizardry to only pick frappe for the chosen version
									options.versions
										.find(v => v.name === benchVersion)
										.apps.find(app => app.name === 'frappe')
								].map(app => {
									return {
										name: app.name,
										source: app.source.name
									};
								}),
								server: server || null
							}
						})
					"
					:loading="$resources.createBench.loading"
				>
					Create Bench
				</Button>
			</div>
		</div>
	</div>
</template>
<script>
import Summary from '../components/Summary.vue';
import Header from '../components/Header.vue';

export default {
	name: 'NewBench',
	components: {
		Summary,
		Header
	},
	props: ['server'],
	data() {
		return {
			benchTitle: '',
			benchVersion: '',
			benchRegion: '',
			agreedToRegionConsent: false
		};
	},
	resources: {
		options() {
			return {
				url: 'press.api.bench.options',
				initialData: {
					versions: [],
					clusters: []
				},
				auto: true
			};
		},
		createBench() {
			return {
				url: 'press.api.bench.new',
				validate() {
					if (!this.benchTitle) {
						return 'Bench Title cannot be blank';
					}
					if (!this.benchVersion) {
						return 'Select a version to create bench';
					}
					if (!this.agreedToRegionConsent) {
						return 'Please agree to the above consent to create bench';
					}
				},
				onSuccess(groupName) {
					this.$router.push({
						name: 'Release Group Detail Apps',
						params: { name: groupName }
					});
				}
			};
		}
	},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		summaryOptions() {
			return [
				{
					label: 'Frappe Framework Version',
					value: this.benchVersion
				},
				{
					label: 'Region',
					value: this.benchRegion,
					condition: () => !this.server
				},
				{
					label: 'Server',
					value: this.server,
					condition: () => this.server
				},
				{
					label: 'Title',
					value: this.benchTitle
				}
			];
		}
	}
};
</script>
