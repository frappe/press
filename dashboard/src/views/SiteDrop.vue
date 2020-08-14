<template>
	<div>
		<Section
			title="Drop Site"
			description="Once you drop your site, there's no going back"
		>
			<Button type="danger" @click="showDialog = true">
				Drop Site
			</Button>
		</Section>
		<Dialog v-model="showDialog" title="Drop Site">
			<p class="text-base">
				Are you sure you want to drop your site? The site will be archived and
				all of its files and Offsite Backups will be deleted. This action cannot be undone.
			</p>
			<p class="mt-4 text-base">
				Please type
				<span class="font-semibold">{{ site.name }}</span> to confirm.
			</p>
			<Input type="text" class="w-full mt-4" v-model="confirmSiteName" />
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
