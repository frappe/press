<template>
	<div>
		<Button variant="ghost" @click="showNewDashboardDialog = true">
			🌟 New dashboard
		</Button>
		<Dialog
			:options="newDashboardDialogOptions"
			v-model="showNewDashboardDialog"
		>
			<template #body-content>
				<div class="prose prose-sm mb-4">
					<p>
						The new dashboard is built from the ground up to provide a better
						experience. You can try it out and let us know what you think.
					</p>
					<p>
						If you find any missing features or bugs, please
						<a href="/support" target="_blank">report them</a> to us and include
						"New Dashboard" in the ticket subject.
					</p>
					<p>
						You can always switch back to the old dashboard from the user
						dropdown on the top-left.
					</p>
				</div>

				<FormControl
					type="checkbox"
					label="Make new dashboard as the default"
					v-model="defaultToNewDashboard"
				/>
			</template>
		</Dialog>
	</div>
</template>
<script>
import FormControl from 'frappe-ui/src/components/FormControl.vue';

export default {
	name: 'TryNewDashboardButton',
	data() {
		return {
			showNewDashboardDialog: false,
			defaultToNewDashboard: Boolean(
				this.$account.team?.default_to_new_dashboard
			)
		};
	},
	resources: {
		changeDefaultDashboard() {
			if (!this.$account.team) return;
			return {
				url: 'press.api.client.run_doc_method',
				params: {
					dt: 'Team',
					dn: this.$account.team.name,
					method: 'change_default_dashboard',
					args: {
						new_dashboard: this.defaultToNewDashboard
					}
				}
			};
		}
	},
	computed: {
		newDashboardDialogOptions() {
			return {
				title: '🌟 New Dashboard',
				actions: [
					{
						label: 'Go to new dashboard',
						variant: 'solid',
						onClick: () => {
							return this.$resources.changeDefaultDashboard.submit(null, {
								onSuccess() {
									this.showNewDashboardDialog = false;
									window.location.href = '/dashboard-beta';
								}
							});
						}
					}
				]
			};
		}
	}
};
</script>
