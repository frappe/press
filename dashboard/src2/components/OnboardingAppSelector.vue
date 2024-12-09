<template>
	<div v-if="apps" class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
		<div
			v-for="app in apps"
			class="flex cursor-pointer flex-col gap-2.5 rounded-md border border-gray-300 p-4 transition duration-300 hover:border-gray-400"
			@click.capture="() => openInstallAppPage(app.name)"
		>
			<img :src="app.image" class="h-6 w-6" />
			<div class="flex flex-col gap-1">
				<p class="text-lg font-medium leading-snug text-gray-900">
					{{ app.title }}
				</p>
				<p
					class="line-clamp-2 text-sm leading-5 tracking-[0.26px] text-gray-700"
				>
					{{ app.description }}
				</p>
			</div>
			<div class="flex w-fit flex-row gap-1 text-gray-600">
				<DownloadIcon class="h-3 w-3" />
				<span class="ml-0.5 text-[12px] leading-3">
					{{ this.$format.numberK(app.total_installs || '0') }} installs
				</span>
			</div>
			<Button size="sm" variant="outline" theme="gray" class="mt-1"
				>Install Now</Button
			>
		</div>
	</div>
</template>
<script>
import DownloadIcon from '~icons/lucide/download';

export default {
	name: 'OnboardingAppSelector',
	props: ['apps'],
	components: {
		DownloadIcon
	},
	methods: {
		openInstallAppPage(app) {
			this.$router.push(`/install-app/${app}`);
		}
	}
};
</script>
