<template>
	<div v-if="apps" class="mt-4 grid grid-cols-1 gap-2">
		<div v-for="app in apps">
			<a
				:href="`/dashboard/install-app/${app.name}`"
				class="focus:shadow-outline group flex cursor-pointer justify-start rounded-lg border p-2 no-underline transition hover:bg-gray-50"
			>
				<img :src="app.image" class="mr-4 h-12 w-12 rounded-md border" />
				<div>
					<span class="text-base font-semibold">{{ app.title }}</span>
					<p class="mt-1 line-clamp-1 text-sm text-gray-600">
						{{ app.description }}
					</p>
				</div>
			</a>
		</div>
	</div>
</template>
<script>
export default {
	name: 'OnboardingAppSelector',
	props: ['apps']
};
</script>
