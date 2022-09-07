<template>
	<div>
		<PageHeader title="Benches" subtitle="Private benches you own">
			<template v-slot:actions>
				<Button
					appearance="primary"
					iconLeft="plus"
					class="ml-2 hidden sm:inline-flex"
					route="/benches/new"
				>
					New
				</Button>
			</template>
		</PageHeader>

		<div>
			<SectionHeader heading="All Benches">
				<template v-slot:actions>
					<SiteAndBenchSearch />
				</template>
			</SectionHeader>

			<div class="mt-3">
				<LoadingText v-if="$resources.allBenches.loading" />
				<BenchList v-else :benches="benches" />
			</div>
		</div>
	</div>
</template>

<script>
import SiteAndBenchSearch from '@/components/SiteAndBenchSearch.vue';
import BenchList from './BenchList.vue';

export default {
	name: 'BenchesScreen',
	pageMeta() {
		return {
			title: 'Benches - Frappe Cloud'
		};
	},
	components: { SiteAndBenchSearch, BenchList },
	resources: {
		allBenches: 'press.api.bench.all'
	},
	computed: {
		benches() {
			if (!this.$resources.allBenches.data) {
				return [];
			}

			return this.$resources.allBenches.data;
		}
	}
};
</script>
