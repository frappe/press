<template>
	<div class="shrink-0">
		<slot v-bind="{ showDialog }"></slot>
		<Dialog v-model="dialogOpen" title="Drop Site">
			<p class="text-base">
				Are you sure you want to drop your site? The site will be archived and
				all of its files and Offsite Backups will be deleted. This action cannot
				be undone.
			</p>
			<p class="mt-4 text-base">
				Please type
				<span class="font-semibold">{{ site.name }}</span> to confirm.
			</p>
			<Input type="text" class="mt-4 w-full" v-model="confirmSiteName" />
			<ErrorMessage class="mt-2" :error="$resources.dropSite.error" />
			<div slot="actions">
				<Button @click="dialogOpen = false"> Cancel </Button>
				<Button
					class="ml-3"
					type="danger"
					@click="$resources.dropSite.submit()"
					:loading="$resources.dropSite.loading"
				>
					Drop Site
				</Button>
			</div>
		</Dialog>
	</div>
</template>

<script>
export default {
	name: 'SiteDrop',
	props: ['site'],
	data() {
		return {
			dialogOpen: false,
			confirmSiteName: null
		};
	},
	resources: {
		dropSite() {
			return {
				method: 'press.api.site.archive',
				params: {
					name: this.site.name
				},
				onSuccess() {
					this.dialogOpen = false;
					this.$router.push('/sites');
				},
				validate() {
					if (this.site.name !== this.confirmSiteName) {
						return 'Please type the site name to confirm';
					}
				}
			};
		}
	},
	methods: {
		showDialog() {
			this.dialogOpen = true;
		}
	}
};
</script>
