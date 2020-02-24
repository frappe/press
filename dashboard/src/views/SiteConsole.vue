<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Access Console</h2>
			<p class="text-gray-600">
				Access your site's Python and Database Console
			</p>
			<Button class="mt-6 hover:bg-gray-100 border">
				Launch Python Console
			</Button>
			<Button class="ml-4 hover:bg-gray-100 border">
				Launch Database Console
			</Button>
		</section>
	</div>
</template>

<script>
export default {
	name: 'SiteConsole',
	props: ['site']
};
</script>
