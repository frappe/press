<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs
				:items="[
					{ label: 'Benches', route: '/benches' },
					{ label: 'New Bench', route: '/benches/new' }
				]"
			/>
		</Header>
	</div>

	<div class="mx-auto max-w-4xl">
		<div v-if="options" class="space-y-12 pb-[50vh] pt-12">
			<div>
				<div class="flex items-center justify-between">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Select Frappe Framework Version
					</h2>
				</div>
				<div class="mt-2">
					<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
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
			<div class="flex flex-col" v-if="options?.clusters.length">
				<h2 class="text-sm font-medium leading-6 text-gray-900">
					Select Region
				</h2>
				<div class="mt-2 w-full space-y-2">
					<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
						<button
							v-for="c in options?.clusters"
							:key="c.name"
							@click="benchRegion = c.name"
							:class="[
								!benchVersion ? 'pointer-events-none' : 'border-gray-400',
								benchRegion === c.name
									? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
									: 'bg-white text-gray-900  ring-gray-200 hover:bg-gray-50',
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
			<div class="flex flex-col">
				<h2 class="text-sm font-medium leading-6 text-gray-900">
					Enter Bench Title
				</h2>
				<div class="mt-2">
					<FormControl
						:disabled="!benchVersion || !benchRegion"
						v-model="benchTitle"
						type="text"
						class="block w-1/2 rounded-md border-gray-300 shadow-sm focus:border-gray-900 focus:ring-gray-900 sm:text-sm"
					/>
				</div>
			</div>
			<div class="flex flex-col space-y-4">
				<FormControl
					type="checkbox"
					:disabled="!benchVersion || !benchRegion || !benchTitle"
					v-model="agreedToRegionConsent"
					:label="`I agree that the laws of the region selected by me shall stand applicable to me and Frappe.`"
				/>
				<ErrorMessage class="my-2" :message="$resources.createBench.error" />
				<Button
					class="w-1/2"
					variant="solid"
					:disabled="!benchVersion || !benchRegion || !benchTitle"
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
								server: null
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
export default {
	name: 'NewBench',
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
		}
	}
};
</script>
