<template>
	<div>
		<PageHeader v-if="appName">
			<template slot="title">
				<div class="flex items-center">
					<a to="/apps" class="flex items-center">
						<FeatherIcon name="arrow-left" class="w-4 h-4" />
						<span class="ml-2 text-base">Back</span>
					</a>
				</div>
			</template>
		</PageHeader>
		<div class="px-4 sm:px-8" v-if="app">
			<div class="border-t"></div>
			<div class="py-8">
				<div class="flex items-center">
					<h1 class="text-2xl font-medium">{{ app.name }}</h1>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'App',
	props: ['appName'],
	resources: {
		app() {
			return {
				method: 'press.api.app.get',
				params: {
					name: this.appName
				},
				auto: true
			};
		}
	},
	computed: {
		app() {
			return this.$resources.app.data;
		}
	}
};
</script>
