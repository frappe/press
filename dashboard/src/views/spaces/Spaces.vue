<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<BreadCrumbs :items="[{ label: 'Spaces', route: '/spaces' }]">
				<template v-if="this.$account.team.enabled" v-slot:actions>
					<Button
						variant="solid"
						iconLeft="plus"
						label="Create"
						class="ml-2"
						@click="showBillingDialog"
					/>
				</template>
			</BreadCrumbs>
		</header>

		<div class="mb-2" v-if="!$account.team.enabled">
			<Alert title="Your account is disabled">
				Enable your account to start creating spaces

				<template #actions>
					<Button variant="solid" route="/settings"> Enable Account </Button>
				</template>
			</Alert>
		</div>

		<div v-if="$resources.allSpaces" class="my-6 mx-5">
			<SectionHeader heading="Code Servers"> </SectionHeader>
			<div class="mt-3 mx-5">
				<LoadingText v-if="$resources.allSpaces.loading" />
				<SpacesList v-else :spaces="$resources.allSpaces.data['spaces']" />
			</div>

			<div class="mt-3 mx-5">
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
