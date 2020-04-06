<template>
	<div>
		<section v-if="teams.length > 1" class="mb-10">
			<h2 class="text-lg font-medium">Team</h2>
			<p class="text-gray-600">
				Teams you are part of and the current active team
			</p>
			<div
				class="w-full py-4 mt-6 border border-gray-100 rounded-md shadow sm:w-1/2"
			>
				<div
					class="grid items-center grid-cols-4 px-6 py-4 hover:bg-gray-50"
					v-for="t in teams"
					:key="t"
				>
					<div class="col-span-3 font-semibold">
						{{ t }}
					</div>

					<div class="w-full text-center">
						<div class="text-sm" v-if="team.name === t">
							Active
						</div>
						<div v-else>
							<Button @click="$store.account.switchToTeam(t)">
								Switch
							</Button>
						</div>
					</div>
				</div>
			</div>
		</section>
		<section>
			<h2 class="text-lg font-medium">Team Members</h2>
			<p class="text-gray-600">
				Team members can access your account on your behalf.
			</p>
			<div
				v-if="team_members.length"
				class="w-full py-4 mt-6 border border-gray-100 rounded-md shadow sm:w-1/2"
			>
				<div
					class="grid items-start grid-cols-4 px-6 py-4 hover:bg-gray-50"
					v-for="member in team_members"
					:key="member.name"
				>
					<div class="col-span-2">
						<div class="font-semibold">
							{{ member.first_name }} {{ member.last_name }}
						</div>
						<div class="text-sm text-gray-600">
							<div>
								{{ member.name }}
							</div>
						</div>
					</div>

					<div>
						{{ getRole(member) }}
					</div>
				</div>
				<div class="px-6 mt-4" v-if="$store.account.hasRole('Press Admin')">
					<Button type="primary" @click="showModal = true">
						Add Member
					</Button>

					<Dialog v-model="showModal" title="Add Member">
						<p class="w-full mt-4">
							Enter the email address of your teammate to invite them.
						</p>
						<input
							type="text"
							class="w-full mt-4 text-gray-900 form-input"
							v-model="memberEmail"
							required
						/>
						<div v-if="errorMessage" class="mt-2 text-sm text-red-600">
							{{ errorMessage }}
						</div>
						<div slot="actions">
							<Button @click="showModal = false">
								Cancel
							</Button>
							<Button
								class="ml-3"
								type="primary"
								:disabled="!memberEmail || state === 'RequestStarted'"
								@click="addMember(memberEmail)"
							>
								Send Invitation
							</Button>
						</div>
					</Dialog>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
import Dialog from '@/components/Dialog';

export default {
	name: 'AccountTeam',
	components: {
		Dialog
	},
	data() {
		return {
			state: null,
			memberEmail: null,
			showModal: false,
			errorMessage: null
		};
	},
	computed: {
		team() {
			return this.$store.account.team;
		},
		team_members() {
			return this.$store.account.team_members;
		},
		teams() {
			return this.$store.account.teams;
		}
	},
	methods: {
		async addMember(email) {
			let team = this.$store.account.team.name;
			await this.$call('press.api.account.add_team_member', { team, email });
			this.showModal = false;
			this.memberEmail = null;

			this.$notify({
				title: 'Invite Sent!',
				message: 'They will receive an email shortly to join your team.',
				color: 'green',
				icon: 'check'
			});
		},
		getRole(member) {
			let roleMap = {
				'Press Admin': 'Owner',
				'Press Member': 'Member'
			};

			let roles = Object.keys(roleMap);
			let role = member.roles?.find(role => {
				return roles.includes(role);
			});
			if (role) {
				return roleMap[role];
			}
			return '';
		}
	}
};
</script>
