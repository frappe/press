<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs :items="[{ label: 'Home', route: { name: 'Home' } }]" />
			<Dropdown
				:options="[
					{ label: 'Site', route: { name: 'NewSite' } },
					{ label: 'Bench', route: { name: 'NewBench' } }
				]"
			>
				<Button
					variant="solid"
					label="Create new"
					:disabled="!$team.doc?.payment_mode"
				>
					<template #suffix>
						<i-lucide-chevron-down class="h-4 w-4 text-gray-300" />
					</template>
				</Button>
			</Dropdown>
		</Header>
	</div>
	<div class="p-5" v-if="$team?.doc">
		<Onboarding v-if="!$team.doc?.onboarding.complete" />
		<HomeSummary v-else />
	</div>
</template>

<script>
import { defineAsyncComponent } from 'vue';
import Header from '../components/Header.vue';
import HomeSummary from '../components/HomeSummary.vue';

export default {
	name: 'Home',
	components: {
		Header,
		HomeSummary,
		Onboarding: defineAsyncComponent(() =>
			import('../components/Onboarding.vue')
		)
	}
};
</script>
