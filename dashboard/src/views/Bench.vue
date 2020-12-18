<template>
	<div>
		<div class="px-4 sm:px-8" v-if="bench">
			<div class="py-8">
				<div class="text-base text-gray-700">
					<router-link to="/benches" class="hover:text-gray-800">
						← Back to Benches
					</router-link>
				</div>
				<div class="flex items-center mt-2">
					<h1 class="text-2xl font-bold">{{ bench.title }}</h1>
					<Badge class="ml-4" :status="bench.status">{{ bench.status }}</Badge>
				</div>
			</div>
		</div>
		<div class="px-4 sm:px-8" v-if="bench">
			<Tabs class="pb-32" :tabs="tabs">
				<router-view v-bind="{ bench }"></router-view>
			</Tabs>
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs';

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
	},
	methods: {
		routeToGeneral() {
			if (this.$route.matched.length === 1) {
				let path = this.$route.fullPath;
				let tab = 'general';
				this.$router.replace(`${path}/${tab}`);
			}
		}
	},
	computed: {
		bench() {
			return this.$resources.bench.data;
		},
		tabs() {
			let tabRoute = subRoute => `/benches/${this.benchName}/${subRoute}`;
			let tabs = [
				{ label: 'General', route: 'general' },
				{ label: 'Apps', route: 'apps' },
				{ label: 'Deploys', route: 'deploys' },
				{ label: 'Jobs', route: 'Jobs' }
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
