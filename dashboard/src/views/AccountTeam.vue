<template>
	<div>
		<Section
			v-if="teams.length > 1"
			class="mb-10"
			title="Team"
			description="Teams you are part of and the current active team"
		>
			<SectionCard>
				<div
					class="grid items-center grid-cols-4 px-6 py-4 hover:bg-gray-50"
					v-for="t in teams"
					:key="t"
				>
					<div class="col-span-3 text-base font-semibold">
						{{ t }}
					</div>

					<div class="w-full text-center">
						<div v-if="team.name === t">
							<Badge color="blue">Active Team</Badge>
						</div>
						<div v-else>
							<Button @click="$account.switchToTeam(t)">
								Switch to Team
							</Button>
						</div>
					</div>
				</div>
			</SectionCard>
		</Section>
		<Section
			title="Team Members"
			description="Team members can access your account on your behalf."
		>
			<SectionCard v-if="team_members.length">
				<div
					class="grid items-start grid-cols-4 px-6 py-4 hover:bg-gray-50"
					v-for="member in team_members"
					:key="member.name"
				>
					<div class="col-span-2">
						<div class="text-base font-semibold">
							{{ member.first_name }} {{ member.last_name }}
						</div>
						<div class="text-sm text-gray-600">
							<div>
								{{ member.name }}
							</div>
						</div>
					</div>

					<div class="text-base">
						<Badge :color="{ Owner: 'blue', Member: 'gray' }[getRole(member)]">
							{{ getRole(member) }}
						</Badge>
					</div>
				</div>
				<div
					class="px-6 mt-4 mb-2"
					v-if="
						$account.hasRole('Press Admin') &&
							($account.team.default_payment_method ||
								$account.team.free_account ||
								$account.team.erpnext_partner)
					"
				>
					<Button type="primary" @click="showModal = true">
						Add Member
					</Button>

					<Dialog v-model="showModal" title="Add Member">
						<Input
							label="Enter the email address of your teammate to invite them."
							type="text"
							class="mt-4"
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
			</SectionCard>
		</Section>
	</div>
</template>

<script>
export default {
	name: 'AccountTeam',
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
			return this.$account.team;
		},
		team_members() {
			return this.$account.team_members;
		},
		teams() {
			return this.$account.teams;
		}
	},
	methods: {
		async addMember(email) {
			let team = this.$account.team.name;
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
