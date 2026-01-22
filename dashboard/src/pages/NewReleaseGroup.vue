<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs
				:items="
					server
						? [
								{
									label: 'Servers',
									route: '/servers',
								},
								{
									label: server,
									route: `/servers/${server}`,
								},
								{
									label: 'New Bench Group',
									route: '/groups/new',
								},
							]
						: [
								{ label: 'Bench Groups', route: '/groups' },
								{ label: 'New Bench Group', route: '/groups/new' },
							]
				"
			/>
		</Header>
	</div>

	<div
		v-if="!$team.doc?.is_desk_user && !$session.hasBenchCreationAccess"
		class="mx-auto mt-60 w-fit rounded border border-dashed px-12 py-8 text-center text-gray-600"
	>
		<lucide-alert-triangle class="mx-auto mb-4 h-6 w-6 text-red-600" />
		<ErrorMessage message="You aren't permitted to create new bench groups" />
	</div>

	<div v-else class="mx-auto max-w-2xl px-5">
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
								'flex cursor-pointer items-center justify-between rounded border border-gray-400 p-3 text-sm focus:outline-none',
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
								'flex w-full items-center rounded border p-3 text-left text-base text-gray-900',
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
					Enter Bench Group Title
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
				<div
					class="flex items-center rounded border border-gray-200 bg-gray-100 p-4 text-sm text-gray-600"
				>
					<lucide-info class="mr-4 inline-block h-6 w-6" />
					<div>
						You can only create USD 25 or higher plan sites in the bench group.
						<a
							href="https://docs.frappe.io/cloud/benches#pricing"
							target="_blank"
							class="underline"
							>Why?</a
						>
					</div>
				</div>
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
								apps: getAppsToInstall(),
								server: server || null,
							},
						})
					"
					:loading="$resources.createBench.loading"
				>
					Create Bench Group
				</Button>
			</div>
		</div>
	</div>
</template>
<script>
import Summary from '../components/Summary.vue';
import Header from '../components/Header.vue';
import { DashboardError } from '../utils/error';
import { h } from 'vue';
import { Badge } from 'frappe-ui';
import ObjectList from '../components/ObjectList.vue';

export default {
	name: 'NewReleaseGroup',
	components: {
		Summary,
		Header,
		ObjectList,
	},
	props: ['server'],
	data() {
		return {
			benchTitle: '',
			benchVersion: '',
			benchRegion: '',
			agreedToRegionConsent: false,
		};
	},
	resources: {
		preInstalledApps() {
			return {
				url: 'press.api.bench.get_default_apps',
				initialData: {},
				auto: true,
			};
		},
		options() {
			return {
				url: 'press.api.bench.options',
				initialData: {
					versions: [],
					clusters: [],
				},
				auto: true,
			};
		},
		createBench() {
			return {
				url: 'press.api.bench.new',
				validate() {
					if (!this.benchTitle) {
						throw new DashboardError('Bench Group Title cannot be blank');
					}
					if (!this.benchVersion) {
						throw new DashboardError('Select a version to create bench');
					}
					if (!this.agreedToRegionConsent) {
						throw new DashboardError(
							'Please agree to the above consent to create bench',
						);
					}
				},
				onSuccess(groupName) {
					this.$router.push({
						name: 'Release Group Detail Apps',
						params: { name: groupName },
					});
				},
			};
		},
	},
	methods: {
		getAppsToInstall() {
			let apps = [
				this.options.versions
					.find((v) => v.name === this.benchVersion)
					.apps.find((app) => app.name === 'frappe'),
			].map((app) => {
				return {
					name: app.name,
					source: app.source.name,
				};
			});

			// add default apps
			apps.push(
				...this.preInstalledApps[this.benchVersion].map((app) => {
					return {
						name: app.app,
						source: app.source,
					};
				}),
			);
			return apps;
		},
	},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		preInstalledApps() {
			return this.$resources.preInstalledApps.data;
		},
		preInstalledAppsList() {
			return {
				data: () => this.preInstalledApps,
				columns: [
					{
						label: 'Default Apps',
						fieldname: 'app_title',
						type: 'Component',
						component: ({ row }) => {
							return h(
								'a',
								{
									class: 'flex items-center text-sm',
									href: `${row.route}`,
									target: '_blank',
								},
								[h('span', { class: 'ml-2' }, row.app_title)],
							);
						},
					},
				],
			};
		},
		summaryOptions() {
			return [
				{
					label: 'Frappe Framework Version',
					value: this.benchVersion,
				},
				{
					label: 'Preinstalled Apps',
					value: this.preInstalledApps[this.benchVersion]
						.map((app) => app.title)
						.join(', '),
					condition: () => this.preInstalledApps[this.benchVersion].length,
				},
				{
					label: 'Region',
					value: this.benchRegion,
					condition: () => !this.server,
				},
				{
					label: 'Server',
					value: this.server,
					condition: () => this.server,
				},
				{
					label: 'Title',
					value: this.benchTitle,
				},
			];
		},
	},
};
</script>
