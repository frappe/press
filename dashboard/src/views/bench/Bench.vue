<template>
	<div>
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
							:label="bench.status"
							:colorMap="$badgeStatusColorMap"
						/>
					</div>
					<div class="flex-row space-x-3 md:flex">
						<Dropdown :options="benchActions">
							<template v-slot="{ open }">
								<Button icon-right="chevron-down">Actions</Button>
							</template>
						</Dropdown>
					</div>
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
				onError: this.$routeTo404PageIfNotFound
			};
		},
		updateAllSites() {
			return {
				method: 'press.api.bench.update_all_sites',
				params: {
					bench_name: this.benchName
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
				{ label: 'Jobs', route: 'jobs' },
				{ label: 'Settings', route: 'setting' }
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
		benchActions() {
			return [
				this.bench.status == 'Active' && {
					label: 'New Site',
					icon: 'plus',
					handler: () => {
						this.$router.push(`/${this.bench.name}/new`);
					}
				},
				this.$account.user.user_type == 'System User' && {
					label: 'View in Desk',
					icon: 'external-link',
					handler: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/release-group/${this.bench.name}`,
							'_blank'
						);
					}
				},
				this.$account.user.user_type == 'System User' && {
					label: 'Impersonate Team',
					icon: 'tool',
					handler: async () => {
						await this.$account.switchTeam(this.bench.team);
						this.$notify({
							title: 'Switched Team',
							message: `Switched to ${this.bench.team}`,
							icon: 'check',
							color: 'green'
						});
					}
				},
				this.bench.status == 'Active' &&
					!this.bench.public && {
						label: 'Update All Sites to Latest Version',
						icon: 'arrow-up-circle',
						handler: async () => {
							await this.$resources.updateAllSites.submit();
							this.$notify({
								title: 'Site update scheduled successfully',
								message: 'All sites in this bench will be updated to the latest version',
								icon: 'check',
								color: 'green'
							});
						}
					}
			].filter(Boolean);
		}
	}
};
</script>
