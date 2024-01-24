<template>
	<Card
		class="h-full max-h-96 min-h-full"
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
		<div class="my-2" v-if="$resources.activities.hasNextPage">
			<Button
				:loading="$resources.activities.list.loading"
				loadingText="Fetching..."
				@click="$resources.activities.next()"
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
				<FormControl v-model="site.notify_email" />
			</template>
		</Dialog>
	</Card>
</template>

<script>
import { notify } from '@/utils/toast';

export default {
	name: 'SiteActivity',
	props: ['site'],
	resources: {
		activities() {
			return {
				type: 'list',
				doctype: 'Site Activity',
				url: 'press.api.site.activities',
				filters: {
					site: this.site?.name
				},
				start: 0,
				auto: true,
				pageLength: 20
			};
		},
		changeNotifyEmail() {
			return {
				url: 'press.api.site.change_notify_email',
				params: {
					name: this.site?.name,
					email: this.site?.notify_email
				},
				onSuccess() {
					this.showChangeNotifyEmailDialog = false;
					notify({
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
