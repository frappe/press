<template>
	<div class="flex-1">
		<div v-if="bench">
			<div class="pb-3">
				<div class="text-base text-gray-700">
					<router-link to="/benches" class="hover:text-gray-800">
						← Back to Benches
					</router-link>
				</div>
				<div
					class="flex flex-col space-y-3 md:flex-row md:items-baseline md:justify-between md:space-y-0"
				>
					<div class="mt-2 flex items-center">
						<h1 class="text-2xl font-bold">{{ bench.title }}</h1>
						<Badge
							class="ml-4"
							:status="bench.status"
							:colorMap="$badgeStatusColorMap"
						>
							{{ bench.status }}
						</Badge>
					</div>
					<span class="flex space-x-1">
						<div v-if="bench.status == 'Active'">
							<Button icon-left="plus" :route="`/${bench.name}/new`">
								New Site
							</Button>
						</div>
						<Button
							v-if="$account.user.user_type == 'System User'"
							icon-left="external-link"
							:link="deskUrl"
						>
							View in Desk
						</Button>
					</span>
				</div>
			</div>
		</div>
		<div>
			<Tabs :tabs="tabs">
				<router-view v-slot="{ Component }">
					<component v-if="bench" :is="Component" :bench="bench"></component>
				</router-view>
			</Tabs>
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs.vue';

export default {
	name: 'Bench',
	pageMeta() {
		return {
			title: `Bench - ${this.bench?.title || 'Private'} - Frappe Cloud`
		};
	},
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
				auto: true,
				onError(e) {
					if (e.indexOf('not found') >= 0) {
						this.$router.push({
							name: 'NotFound',
							// preserve current path and remove the first char to avoid the target URL starting with `//`
							params: { pathMatch: this.$route.path.substring(1).split('/') },
							// preserve existing query and hash if any
							query: this.$route.query,
							hash: this.$route.hash
						});
					}
				}
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
		},
		isSaasLogin(app) {
			if (localStorage.getItem('saas_login')) {
				return `/saas/manage/${app}/benches`;
			}

			return '/sites';
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
				{ label: 'Apps', route: 'apps' },
				{ label: 'Versions', route: 'versions' },
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
		},
		deskUrl() {
			return `${window.location.protocol}//${window.location.host}/app/release-group/${this.bench.name}`;
		}
	}
};
</script>
