<template>
	<div class="sm:grid sm:grid-cols-2">
		<Card title="Settings">
			<!--<ListItem
				v-if="props.site.status !== 'Pending'"
				title="Drop Site"
				description="Once you drop site your site, there is no going back"
			>
				<template v-slot:actions>
					<SiteDrop :site="this.props.site" v-slot="{ showDialog }">
						<Button @click="showDialog">
							<span class="text-red-600">Drop Site</span>
						</Button>
					</SiteDrop>
				</template>
			</ListItem> -->
			<ListItem
				v-if="site.status == 'Active'"
				title="Deactivate Subscription"
				description="The subscription will go inactive and site won't be publicly accessible, also the billing will stop"
			>
				<template v-slot:actions>
					<Button @click="onDeactivateClick" class="shrink-0">
						Deactivate
					</Button>
				</template>
			</ListItem>

			<ListItem
				v-if="site.status == 'Inactive'"
				title="Activate Subscription"
				description="The subscription will become active and billing will be resumed"
			>
				<template v-slot:actions>
					<Button @click="onActivateClick" class="shrink-0"> Activate </Button>
				</template>
			</ListItem>
		</Card>
	</div>
</template>

<script>
export default {
	name: 'SubscriptionSettings',
	props: ['site', 'subName'],
	data() {
		return {
			dialogOpen: true
		};
	},
	methods: {
		onDeactivateClick() {
			this.$confirm({
				title: 'Deactivate Subscription',
				message: `
					Are you sure you want to deactivate this subscription? The site will go in an inactive state.
					It won't be accessible.
				`,
				actionLabel: 'Deactivate',
				actionType: 'danger',
				action: () => this.deactivate()
			});
		},
		onActivateClick() {
			this.$confirm({
				title: 'Activate Subscription',
				message: 'Are you sure you want to activate this subscription?',
				actionLabel: 'Activate',
				actionType: 'primary',
				action: () => this.activate()
			});
		},
		deactivate() {
			return this.$call('press.api.saas.deactivate', {
				name: this.subName
			}).then(() => {
				setTimeout(() => window.location.reload(), 1000);
			});
		},
		activate() {
			this.$call('press.api.saas.activate', {
				name: this.subName
			});
			this.$notify({
				title: 'Site activated successfully!',
				message: 'You can now access your site',
				icon: 'check',
				color: 'green'
			});
			setTimeout(() => window.location.reload(), 1000);
		}
	}
};
</script>
