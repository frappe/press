<template>
	<div v-if="stack">
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<Breadcrumbs
				:items="[
					{ label: 'Stacks', route: { name: 'StacksScreen' } },
					{
						label: stack?.title,
						route: {
							name: 'StackServices',
							params: { stackName: stack?.name }
						}
					}
				]"
			>
				<template #actions>
					<div>
						<Dropdown :options="stackActions">
							<template v-slot="{ open }">
								<Button variant="ghost" class="mr-2" icon="more-horizontal" />
							</template>
						</Dropdown>
					</div>
				</template>
			</Breadcrumbs>
		</header>

		<div class="p-5">
			<div
				class="flex flex-col space-y-3 md:flex-row md:items-baseline md:justify-between md:space-y-0"
			>
				<div class="flex items-center">
					<h1 class="text-2xl font-bold">{{ stack.title }}</h1>
					<Badge class="ml-4" :label="stack.status" />
				</div>
			</div>
			<div class="mb-2 mt-4">
				<AlertStackUpdate :stack="stack" />
			</div>
			<Tabs :tabs="tabs">
				<router-view v-slot="{ Component }">
					<component v-if="stack" :is="Component" :stack="stack"></component>
				</router-view>
			</Tabs>
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs.vue';
import AlertStackUpdate from '@/components/AlertStackUpdate.vue';
import { notify } from '@/utils/toast';

export default {
	name: 'Stack',
	pageMeta() {
		return {
			title: `Stack - ${this.stack?.title || 'Private'} - Frappe Cloud`
		};
	},
	props: ['stackName'],
	components: {
		Tabs,
		AlertStackUpdate
	},
	resources: {
		stack() {
			return {
				url: 'press.api.stack.get',
				params: {
					name: this.stackName
				},
				auto: true,
				onError: this.$routeTo404PageIfNotFound
			};
		},
		Statusstack() {
			return {
				url: 'press.api.stack.get',
				params: {
					name: this.stackName
				},
				onSuccess(response) {
					console.log(response);
					this.$resources.stack.data.status = response.status;
				}
			};
		}
	},
	activated() {
		this.$socket.on('stack_update', this.onSocketUpdate);
	},
	deactivated() {
		this.$socket.off('stack_update', this.onSocketUpdate);
	},
	methods: {
		onSocketUpdate({ doctype, name }) {
			if (doctype == 'Stack' && name == this.stack.name) {
				this.reloadStack();
			}
		},
		reloadStack() {
			// reload if not loaded in last 1 second
			let seconds = 1;
			if (new Date() - this.$resources.stack.lastLoaded > 1000 * seconds) {
				this.$resources.stack.reload();
			}
		}
	},
	computed: {
		stack() {
			if (this.$resources.stack?.data && !this.$resources.stack.loading) {
				return this.$resources.stack.data;
			}
		},
		tabs() {
			let tabRoute = subRoute => `/stacks/${this.stackName}/${subRoute}`;
			let tabs = [
				{ label: 'Services', route: 'services' },
				{ label: 'Deploys', route: 'deploys' },
				{ label: 'Jobs', route: 'jobs' }
			].filter(tab => (tab.condition ? tab.condition() : true));

			if (this.stack) {
				return tabs.map(tab => {
					return {
						...tab,
						route: tabRoute(tab.route)
					};
				});
			}
			return [];
		},
		stackActions() {
			return [
				['Active', 'Updating'].includes(this.stack?.status) && {
					label: 'Visit Site',
					icon: 'external-link',
					onClick: () => {
						window.open(`https://${this.stack?.title}`, '_blank');
					}
				},
				{
					label: 'View in Desk',
					icon: 'external-link',
					condition: () => this.$account.user.user_type == 'System User',
					onClick: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/release-group/${this.stack.name}`,
							'_blank'
						);
					}
				},
				{
					label: 'Impersonate Team',
					icon: 'tool',
					condition: () => this.$account.user.user_type == 'System User',
					onClick: async () => {
						await this.$account.switchTeam(this.stack.team);
						notify({
							title: 'Switched Team',
							message: `Switched to ${this.stack.team}`,
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
