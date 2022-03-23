<template>
	<div class="mt-10">
		<div class="px-4 sm:px-8" v-if="bench">
			<div class="pb-3">
				<div class="text-base text-gray-700">
					<router-link to="/sites" class="hover:text-gray-800">
						← Back to Benches
					</router-link>
				</div>
				<div
					class="flex flex-col space-y-3 md:flex-row md:items-baseline md:justify-between md:space-y-0"
				>
					<div class="mt-2 flex items-center">
						<h1 class="text-2xl font-bold">{{ bench.title }}</h1>
						<Badge class="ml-4" :status="bench.status">
							{{ bench.status }}
						</Badge>
					</div>
					<div v-if="bench.status == 'Active'">
						<Button icon-left="plus" :route="`/${bench.name}/new`">
							New Site
						</Button>
					</div>
				</div>
			</div>
		</div>
		<div class="px-4 sm:px-8">
			<Tabs class="pb-32" :tabs="tabs">
				<router-view v-bind="{ bench }"></router-view>
			</Tabs>
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs.vue';

export default {
	name: 'Bench',
	props: ['benchName'],
	components: {
		Tabs
	},
	resources: {
		bench() {
			return {
				method: 'press.api.bench.get',
				params: {
					name: this.benchName
				},
				auto: true
			};
		}
	},
	activated() {
		this.routeToGeneral();
		this.$socket.on('list_update', this.onSocketUpdate);
	},
	deactivated() {
		this.$socket.off('list_update', this.onSocketUpdate);
	},
	methods: {
		onSocketUpdate({ doctype, name }) {
			if (doctype == 'Release Group' && name == this.bench.name) {
				this.reloadBench();
			}
		},
		routeToGeneral() {
			if (this.$route.matched.length === 1) {
				let path = this.$route.fullPath;
				let tab = 'overview';
				this.$router.replace(`${path}/${tab}`);
			}
		},
		reloadBench() {
			// reload if not loaded in last 1 second
			let seconds = 1;
			if (new Date() - this.$resources.bench.lastLoaded > 1000 * seconds) {
				this.$resources.bench.reload();
			}
		}
	},
	computed: {
		bench() {
			if (this.$resources.bench.data && !this.$resources.bench.loading) {
				return this.$resources.bench.data;
			}
		},
		tabs() {
			let tabRoute = subRoute => `/benches/${this.benchName}/${subRoute}`;
			let tabs = [
				{ label: 'Overview', route: 'overview' },
				{ label: 'Sites', route: 'sites' },
				{ label: 'Deploys', route: 'deploys' },
				{ label: 'Jobs', route: 'jobs' }
			];
			if (this.bench) {
				return tabs.map(tab => {
					return {
						...tab,
						route: tabRoute(tab.route)
					};
				});
			}
			return [];
		}
	}
};
</script>
