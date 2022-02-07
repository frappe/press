<template>
	<ul class="space-y-2 text-sm text-gray-700">
		<li
			class="flex flex-row justify-items-center"
			v-for="feature in features"
			:key="feature"
		>
			<CircularCheckIcon class="mr-2" />
			{{ feature }}
		</li>
	</ul>
</template>

<script>
export default {
	name: 'FeatureList',
	props: ['features']
};
</script>
