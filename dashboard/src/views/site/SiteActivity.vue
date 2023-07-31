<template>
	<Card
		class="min-h-full h-full max-h-96"
		title="Site Activity"
		subtitle="Log of activities performed on your site"
	>
		<div class="divide-y">
			<ListItem
				v-for="a in activities.data"
				:key="a.creation"
				:title="`${a.action} by ${a.owner}`"
				:description="getDescription(a)"
			/>
		</div>
		<div class="my-2" v-if="!$resources.activities.lastPageEmpty">
			<Button
				:loading="$resources.activities.loading"
				loadingText="Fetching..."
				@click="pageStart += 20"
			>
				Load more
			</Button>
		</div>

		<template v-slot:actions>
			<Button @click="showChangeNotifyEmailDialog = true">
				Change Notify Email
			</Button>
		</template>
		<Dialog
			:options="{
				title: 'Change Notify Email',
				actions: [
					{
						label: 'Save Changes',
						variant: 'solid',
						loading: $resources.changeNotifyEmail.loading,
						onClick: () => $resources.changeNotifyEmail.submit()
					}
				]
			}"
			v-model="showChangeNotifyEmailDialog"
		>
			<template v-slot:body-content>
				<Input v-model="site.notify_email" />
			</template>
		</Dialog>
	</Card>
</template>

<script>
export default {
	name: 'SiteActivity',
	props: ['site'],
	resources: {
		activities() {
			return {
				method: 'press.api.site.activities',
				params: {
					name: this.site?.name,
					start: this.pageStart
				},
				auto: true,
				pageLength: 20,
				keepData: true
			};
		},
		changeNotifyEmail() {
			return {
				method: 'press.api.site.change_notify_email',
				params: {
					name: this.site?.name,
					email: this.site?.notify_email
				},
				onSuccess() {
					this.showChangeNotifyEmailDialog = false;
					this.$notify({
						title: 'Notify Email Changed!',
						icon: 'check',
						color: 'green'
					});
				}
			};
		}
	},
	computed: {
		activities() {
			return this.$resources.activities;
		}
	},
	data() {
		return {
			pageStart: 0,
			showChangeNotifyEmailDialog: false
		};
	},
	methods: {
		getDescription(activity) {
			let description = '';
			if (activity.reason) {
				description += `Reason: ${activity.reason}\n`;
			}
			description += this.formatDate(activity.creation);
			return description;
		}
	}
};
</script>
