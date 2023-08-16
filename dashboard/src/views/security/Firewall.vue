<template>
	<div>
		<div class="mx-5 mt-5">
			<div class="flex">
				<div class="flex w-full space-x-2 pb-4">
					<FormControl v-model="searchTerm">
						<template #prefix>
							<FeatherIcon name="search" class="w-4 text-gray-600" />
						</template>
					</FormControl>
				</div>
			</div>
			<LoadingText v-if="$resources.FirewallRules.loading" />
			<div v-else>
				<div class="flex">
					<div class="flex w-full px-3 py-4">
						<div class="w-2/12 text-base font-medium text-gray-900">
							Protocol
						</div>
						<div class="w-2/12 text-base font-medium text-gray-900">
							Port Range
						</div>
						<div class="w-2/12 text-base font-medium text-gray-900">Source</div>
						<div class="w-2/12 text-base font-medium text-gray-900">Action</div>
						<div class="w-4/12 text-base font-medium text-gray-900">
							Description
						</div>
					</div>
				</div>
				<div class="w-8" />
			</div>
			<div class="mx-2.5 border-b" />
			<FirewallRule :rules="rules" />
		</div>
	</div>
</template>

<script>
import FirewallRule from './FirewallRule.vue';

export default {
	name: 'Firewall',
	props: ['server'],
	components: {
		FirewallRule
	},
	resources: {
		FirewallRules() {
			return {
				method: 'press.api.security.get_firewall_rules',
				params: {
					server: this.server?.name,
					server_type: this.server?.server_type
				},
				auto: true,
				onError: this.$routeTo404PageIfNotFound
			};
		}
	},
	computed: {
		rules() {
			return this.$resources.FirewallRules.data;
		}
	}
};
</script>
