<template>
	<div>
		<Button
			v-if="$resources.apps.loading"
			:loading="true"
			loadingText="Loading..."
		></Button>
		<ul v-else>
			<li v-for="app in $resources.apps.data" :key="app.name">{{ app.title }}</li>
		</ul>
	</div>
</template>

<script>
export default {
	name: 'DeveloperApps',
	resources: {
		apps() {
			return {
				method: 'press.api.developer.get_apps',
				auto: true
			};
		}
	}
};
</script>
