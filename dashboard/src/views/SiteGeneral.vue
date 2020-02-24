<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Site information</h2>
			<p class="text-gray-600">General information about your site</p>
			<div class="w-1/2 mt-6 border border-gray-100 shadow rounded px-6 py-4">
				<div class="flex py-1">
					<div class="w-56">Site name:</div>
					<div class="font-medium">{{ site.name }}</div>
				</div>
				<div class="flex py-1">
					<div class="w-56">Created:</div>
					<div class="font-medium">
						<FormatDate>{{ site.creation }}</FormatDate>
					</div>
				</div>
				<div class="flex py-1">
					<div class="w-56">Last update:</div>
					<div class="font-medium">
						<FormatDate>{{ site.modified }}</FormatDate>
					</div>
				</div>
			</div>
		</section>
		<section class="mt-10">
			<h2 class="font-medium text-lg">Installed apps</h2>
			<p class="text-gray-600">Apps installed on your site</p>
			<div class="w-1/2 mt-6 border border-gray-100 shadow rounded px-6 py-4">
				<div class="flex py-1" v-for="app in site.apps">
					<div class="w-56">
                        {{ app.app }}
                    </div>
					<div class="font-medium">
						v12.1.1
					</div>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
export default {
	name: 'SiteGeneral',
	props: ['site']
};
</script>
