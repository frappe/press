<template>
    <ul class="text-base text-gray-700 space-y-2">
			<li
				class="flex flex-row items-center"
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
}
</script>