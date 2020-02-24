<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Drop Site</h2>
			<p class="text-gray-600">
				Once you drop your site, there's no going back
			</p>
			<Button class="mt-6 bg-red-500 hover:bg-red-600 text-white">Drop Site</Button>
		</section>
	</div>
</template>

<script>
export default {
	name: 'SiteConsole',
	props: ['site']
};
</script>
