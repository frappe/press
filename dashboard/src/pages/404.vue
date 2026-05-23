<template>
	<div class="flex h-screen flex-col items-center justify-center p-5">
		<div class="text-[4rem] text-ink-gray-9">404</div>
		<div class="text-base text-ink-gray-6">Page non trouvée</div>
		<Button class="mt-4" route="/sites" variant="outline">
			Aller à la liste des sites
		</Button>
	</div>
</template>

<script>
export default {
	name: '404NotFound',
	data() {
		return {
			surprise: false,
		};
	},
};
</script>
