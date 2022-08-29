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
	</div>
</template>

<script>
import PageHeader from '@/components/global/PageHeader.vue';
export default {
	name: 'BenchesScreen',
	components: { PageHeader }
};
</script>
