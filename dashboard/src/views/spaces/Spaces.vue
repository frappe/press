<template>
	<div>
		<PageHeader title="Spaces" subtitle="Your Frappe Spaces and Code Servers">
			<template v-if="this.$account.team.enabled" v-slot:actions>
				<Button
					appearance="primary"
					iconLeft="plus"
					class="ml-2"
					@click="showBillingDialog"
				>
					New
				</Button>
			</template>
		</PageHeader>

		<div class="mb-2" v-if="!$account.team.enabled">
			<Alert title="Your account is disabled">
				Enable your account to start creating spaces

				<template #actions>
					<Button appearance="primary" route="/settings">
						Enable Account
					</Button>
				</template>
			</Alert>
		</div>

		<div v-if="$resources.allSpaces" class="mb-6">
			<SectionHeader heading="Code Servers"> </SectionHeader>
			<div class="mt-3">
				<LoadingText v-if="$resources.allSpaces.loading" />
				<SpacesList v-else :spaces="$resources.allSpaces.data['spaces']" />
			</div>

			<div class="mt-3">
				<LoadingText v-if="$resources.allSpaces.loading" />
				<CodeServersList
					v-else
					:servers="$resources.allSpaces.data['servers']"
				/>
			</div>
		</div>
	</div>
</template>

<script>
import SpacesList from './SpacesList.vue';
import CodeServersList from './CodeServersList.vue';

export default {
	name: 'Spaces',
	components: {
		SpacesList,
		CodeServersList
	},
	data() {
		return {
			recentlyCreatedSites: []
		};
	},
	resources: {
		allSpaces() {
			return {
				method: 'press.api.spaces.spaces',
				auto: true
			};
		}
	},
	methods: {
		showBillingDialog() {
			if (!this.$account.hasBillingInfo) {
				this.showAddCardDialog = true;
			} else {
				this.$router.replace('/codeservers/new');
			}
		}
	}
};
</script>
