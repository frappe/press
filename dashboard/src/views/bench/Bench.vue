<template>
	<div v-if="bench">
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<BreadCrumbs
				:items="[
					{ label: 'Benches', route: { name: 'BenchesScreen' } },
					{
						label: bench?.title,
						route: {
							name: 'BenchOverview',
							params: { benchName: bench?.name }
						}
					}
				]"
			>
				<template #actions>
					<div>
						<Dropdown :options="benchActions">
							<template v-slot="{ open }">
								<Button variant="ghost" class="mr-2" icon="more-horizontal" />
							</template>
						</Dropdown>
						<Button
							v-if="bench?.status === 'Active'"
							variant="solid"
							icon-left="plus"
							label="New Site"
							@click="$router.push(`/${this.bench.name}/new`)"
						/>
					</div>
				</template>
			</BreadCrumbs>
		</header>

		<EditBenchTitleDialog v-model="showEditTitleDialog" :bench="bench" />

		<div class="p-5">
			<div
				class="flex flex-col space-y-3 md:flex-row md:items-baseline md:justify-between md:space-y-0"
			>
				<div class="flex items-center">
					<h1 class="text-2xl font-bold">{{ bench.title }}</h1>
					<Badge class="ml-4" :label="bench.status" />
				</div>
			</div>
			<div class="mb-2 mt-4">
				<AlertBenchUpdate v-if="bench?.no_sites <= 0" :bench="bench" />
				<AlertUpdate v-else :bench="bench" />
			</div>
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
import AlertUpdate from '@/components/AlertUpdate.vue';
import AlertBenchUpdate from '@/components/AlertBenchUpdate.vue';
import EditBenchTitleDialog from './EditBenchTitleDialog.vue';

export default {
	name: 'Bench',
	pageMeta() {
		return {
			title: `Bench - ${this.bench?.title || 'Private'} - Frappe Cloud`
		};
	},
	props: ['benchName'],
	components: {
		Tabs,
		AlertUpdate,
		AlertBenchUpdate,
		EditBenchTitleDialog
	},
	data() {
		return {
			showEditTitleDialog: false
		};
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
			if (this.$resources.bench?.data && !this.$resources.bench.loading) {
				return this.$resources.bench.data;
			}
		},
		tabs() {
			let tabRoute = subRoute => `/benches/${this.benchName}/${subRoute}`;
			let tabs = [
				{
					label: 'Sites',
					route: 'sites'
				},
				{ label: 'Overview', route: 'overview' },
				{ label: 'Apps', route: 'apps' },
				{ label: 'Versions', route: 'versions' },
				{ label: 'Deploys', route: 'deploys' },
				{
					label: 'Config',
					route: 'bench-config'
				},
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
				{
					label: 'Edit Title',
					icon: 'edit',
					onClick: () => (this.showEditTitleDialog = true)
				},
				{
					label: 'View in Desk',
					icon: 'external-link',
					condition: () => this.$account.user.user_type == 'System User',
					onClick: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/release-group/${this.bench.name}`,
							'_blank'
						);
					}
				},
				{
					label: 'Impersonate Team',
					icon: 'tool',
					condition: () => this.$account.user.user_type == 'System User',
					onClick: async () => {
						await this.$account.switchTeam(this.bench.team);
						this.$notify({
							title: 'Switched Team',
							message: `Switched to ${this.bench.team}`,
							icon: 'check',
							color: 'green'
						});
					}
				},
				{
					label: 'Update All Sites to Latest Version',
					icon: 'arrow-up-circle',
					condition: () => this.bench.status == 'Active' && !this.bench.public,
					onClick: async () => {
						await this.$resources.updateAllSites.submit();
						this.$notify({
							title: 'Site update scheduled successfully',
							message:
								'All sites in this bench will be updated to the latest version',
							icon: 'check',
							color: 'green'
						});
					}
				}
			];
		}
	}
};
</script>
