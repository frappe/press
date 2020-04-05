<template>
	<div>
		<section>
			<h2 class="text-lg font-medium">Drop Site</h2>
			<p class="text-gray-600">
				Once you drop your site, there's no going back
			</p>
			<Button class="mt-6" type="danger" @click="showDialog = true">
				Drop Site
			</Button>
		</section>
		<Dialog v-model="showDialog" title="Drop Site">
			<p>
				Are you sure you want to drop your site? The site will be archived and
				all of its files will be deleted. This action cannot be undone.
			</p>
			<p class="mt-4">
				Please type
				<span class="font-semibold">{{ site.name }}</span> to confirm.
			</p>
			<input
				type="text"
				class="w-full mt-4 text-gray-900 form-input"
				v-model="confirmSiteName"
			/>
			<div slot="actions">
				<Button @click="showDialog = false">
					Cancel
				</Button>
				<Button
					class="ml-3"
					type="danger"
					:disabled="site.name !== confirmSiteName"
					@click="dropSite"
				>
					Drop Site
				</Button>
			</div>
		</Dialog>
	</div>
</template>

<script>
import Dialog from '@/components/Dialog';
export default {
	name: 'SiteDrop',
	props: ['site'],
	components: {
		Dialog
	},
	data() {
		return {
			showDialog: false,
			confirmSiteName: null
		};
	},
	methods: {
		async dropSite() {
			await this.$call('press.api.site.archive', { name: this.site.name });
			this.showDialog = false;
			this.$router.push(`/sites`);
		}
	}
};
</script>
