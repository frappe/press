<template>
	<PressUIAction name="Change Team">
		<div>
			<Button @click="showDialog = true">
				Change Team
			</Button>
			<Dialog title="Change Team" v-model="showDialog">
				<Input
					label="Select Team"
					type="text"
					list="teamList"
					v-model="team"
					@input="fetchTeams"
				/>
				<datalist id="teamList">
					<option v-for="d in $resources.teams.data || []" :value="d.name" />
				</datalist>

				<template #actions>
					<Button type="primary" @click="switchTeam">Change</Button>
				</template>
			</Dialog>
		</div>
	</PressUIAction>
</template>
<script>
import debounce from 'lodash/debounce';
export default {
	name: 'ChangeTeamButton',
	data() {
		return {
			showDialog: false,
			team: null,
			suggestions: []
		};
	},
	resources: {
		teams() {
			let filters = {};
			if (this.team) {
				filters.name = ['like', `%${this.team}%`];
			}
			return {
				method: 'frappe.client.get_list',
				params: {
					doctype: 'Team',
					filters
				}
			};
		}
	},
	methods: {
		fetchTeams: debounce(function() {
			this.$resources.teams.fetch();
		}, 300),
		switchTeam() {
			if (this.team) {
				this.$account.switchToTeam(this.team);
			}
		}
	}
};
</script>
