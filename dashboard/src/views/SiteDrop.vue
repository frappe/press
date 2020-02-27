<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Drop Site</h2>
			<p class="text-gray-600">
				Once you drop your site, there's no going back
			</p>
			<Button
				class="mt-6 bg-red-500 hover:bg-red-600 text-white"
				@click="showModal = true"
			>
				Drop Site
			</Button>
		</section>
		<Modal :show="showModal" @hide="showModal = false">
			<div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
				<div class="sm:flex sm:items-start">
					<div class="mt-3 sm:mt-0 sm:text-left">
						<h3 class="text-xl leading-6 font-medium text-gray-900">
							Drop Site
						</h3>
						<div class="mt-4 leading-5 text-gray-800">
							<p>
								Are you sure you want to drop your site? The site will be
								archived and all of its files will be deleted. This action
								cannot be undone.
							</p>
							<p class="mt-4">
								Please type
								<span class="font-semibold">{{ site.name }}</span> to confirm.
							</p>
							<input
								type="text"
								class="mt-4 form-input text-gray-900 w-full"
								v-model="confirmSiteName"
							/>
						</div>
					</div>
				</div>
			</div>
			<div class="p-4 sm:px-6 sm:py-4 flex items-center justify-end">
				<span class="flex rounded-md shadow-sm">
					<Button class="border hover:bg-gray-100" @click="showModal = false">
						Cancel
					</Button>
				</span>
				<span class="flex rounded-md shadow-sm ml-3">
					<Button
						class="text-white"
						:class="
							site.name !== confirmSiteName
								? 'bg-red-300'
								: 'bg-red-500 hover:bg-red-600'
						"
						:disabled="site.name !== confirmSiteName"
						@click="dropSite"
					>
						Drop Site
					</Button>
				</span>
			</div>
		</Modal>
	</div>
</template>

<script>
import Modal from '@/components/Modal';
export default {
	name: 'SiteDrop',
	props: ['site'],
	components: {
		Modal
	},
	data() {
		return {
			showModal: false,
			confirmSiteName: null
		};
	},
	methods: {
		async dropSite() {
			await this.$call('press.api.site.archive', { name: this.site.name });
		}
	}
};
</script>
