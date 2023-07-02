<template>
	<div>
		<PageHeader title="Servers" subtitle="Your Servers">
			<template v-if="this.$account.team.enabled" v-slot:actions>
				<Dropdown
					v-if="
						$account.team.self_hosted_servers_enabled === 1 &&
						!showAddCardDialog
					"
					:options="dropDownOptions"
				>
					<!-- <template v-slot="{ open }"> -->
					<Button
						appearance="primary"
						iconLeft="plus"
						class="ml-2 hidden sm:inline-flex"
						@click="showBillingDialog"
					>
						New
					</Button>
					<!-- </template> -->
				</Dropdown>
				<Button
					v-else
					appearance="primary"
					iconLeft="plus"
					class="ml-2 hidden sm:inline-flex"
					@click="showBillingDialog"
				>
					New
				</Button>
			</template>
		</PageHeader>

		<div>
			<div class="mt-3">
				<SectionHeader class="mb-2" heading="">
					<template #actions>
						<Input
							v-if="$resources.allServers.data"
							type="select"
							:options="['Filter by Tag', ...$resources.allServers.data.tags]"
							v-model="selectedTag"
							class="w-32"
						/>
					</template>
				</SectionHeader>
				<LoadingText v-if="$resources.allServers.loading" />
				<ServerList v-else :servers="filteredServers(servers)" />
			</div>
		</div>
		<Dialog
			:options="{ title: 'Add card to create new servers' }"
			v-model="showAddCardDialog"
		>
			<template v-slot:body-content>
				<StripeCard
					class="mb-1"
					v-if="showAddCardDialog"
					@complete="
						showAddCardDialog = false;
						$resources.paymentMethods.reload();
					"
				/>
			</template>
		</Dialog>
	</div>
</template>
<script>
import ServerList from '@/views/server/ServerList.vue';
import PageHeader from '@/components/global/PageHeader.vue';
import Dropdown from 'frappe-ui/src/components/Dropdown.vue';
import { defineAsyncComponent } from 'vue';

export default {
	name: 'Servers',
	components: {
		ServerList,
		PageHeader,
		StripeCard: defineAsyncComponent(() =>
			import('@/components/StripeCard.vue')
		),
		Dropdown
	},
	data() {
		return {
			showAddCardDialog: false,

			dropDownOptions: [
				{
					label: 'Frappe Cloud Server',
					handler: () => this.$router.replace('/servers/new')
				},
				{
					label: 'Self Hosted Server',
					handler: () => this.$router.replace('/selfhosted/new')
				}
			],
			selectedTag: ''
		};
	},
	resources: {
		allServers: {
			method: 'press.api.server.all',
			auto: true
		}
	},
	methods: {
		reload() {
			// refresh if currently not loading and have not reloaded in the last 5 seconds
			if (
				!this.$resources.allServers.loading &&
				new Date() - this.$resources.allServers.lastLoaded > 5000
			) {
				this.$resources.allServers.reload();
			}
		},
		showBillingDialog() {
			if (!this.$account.hasBillingInfo) {
				this.showAddCardDialog = true;
			} else {
				if (this.$account.team.self_hosted_servers_enabled !== 1) {
					this.$router.replace('/servers/new');
				}
				this.showAddCardDialog = false;
			}
		},
		filteredServers(servers) {
			if (!this.selectedTag || this.selectedTag === 'Filter by Tag') {
				return servers;
			}

			return servers.filter(server => server.tags.includes(this.selectedTag));
		}
	},
	computed: {
		servers() {
			if (!this.$resources.allServers.data) {
				return [];
			}
			return this.$resources.allServers.data.servers;
		}
	}
};
</script>
