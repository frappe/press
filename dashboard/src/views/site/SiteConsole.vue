<template>
	<div>
		<section>
			<h2 class="text-lg font-medium">Access Console</h2>
			<p class="text-gray-600">
				Access your site's Python and Database Console
			</p>
			<div class="flex">
				<Button class="mt-6"> Launch Python Console </Button>
				<Button class="mt-6 ml-4"> Launch Database Console </Button>
			</div>
		</section>
	</div>
</template>

<script>
export default {
	name: 'SiteConsole',
	props: ['site']
};
</script>
