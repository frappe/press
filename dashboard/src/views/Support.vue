<template>
	<div>
		<PageHeader>
			<template slot="title">
				<div class="flex items-center">
					<a @click.prevent="$router.back()" class="flex items-center" href="#">
						<FeatherIcon name="arrow-left" class="w-4 h-4" />
						<span class="ml-2 text-base">Back</span>
					</a>
				</div>
			</template>
		</PageHeader>
		<div class="p-24 text-center">
			<div class="text-xl text-gray-800">
				For support, join Frappe Cloud group on Telegram
			</div>
			<Button class="mt-10" type="primary">
				<a href="https://t.me/frappecloud" target="_blank">
					Join t.me/frappecloud
				</a>
			</Button>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Support'
};
</script>
