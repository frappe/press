<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Team</h2>
			<p class="text-gray-600">
				Teams you are part of and the current active team.
			</p>
			<div
				class="w-full sm:w-1/2 mt-6 border border-gray-100 shadow rounded-md py-4"
			>
				<div
					class="px-6 py-4 grid grid-cols-4 items-center hover:bg-gray-50"
					v-for="t in teams"
					:key="t"
				>
					<div class="font-semibold col-span-3">
						{{ t }}
					</div>

					<div class="text-center w-full">
						<div class="text-sm" v-if="team.name === t">
							Active
						</div>
						<div v-else>
							<Button
								@click="$store.account.switchToTeam(t)"
								class="border hover:bg-gray-100 text-sm"
							>
								Switch
							</Button>
						</div>
					</div>
				</div>
			</div>
		</section>
		<section class="mt-10">
			<h2 class="font-medium text-lg">Team Members</h2>
			<p class="text-gray-600">
				Team members can access your account on your behalf.
			</p>
			<div
				v-if="team_members.length"
				class="w-full sm:w-1/2 mt-6 border border-gray-100 shadow rounded-md py-4"
			>
				<div
					class="px-6 py-4 grid grid-cols-4 items-start hover:bg-gray-50"
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
					<Button
						class="bg-blue-500 text-white hover:bg-blue-600"
						@click="showModal = true"
					>
						Add Member
					</Button>

					<Modal :show="showModal" @hide="showModal = false">
						<div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
							<div class="sm:flex sm:items-start">
								<div class="mt-3 sm:mt-0 sm:text-left w-full">
									<h3 class="text-xl leading-6 font-medium text-gray-900">
										Add Member
									</h3>
									<div class="mt-4 leading-5 text-gray-800">
										<p class="mt-4 w-full">
											Enter the email address of your teammate to invite them.
										</p>
										<input
											type="text"
											class="mt-4 form-input text-gray-900 w-full"
											v-model="memberEmail"
											required
										/>
									</div>
								</div>
							</div>
							<div v-if="errorMessage" class="mt-2 text-sm text-red-600">
								{{ errorMessage }}
							</div>
						</div>
						<div class="p-4 sm:px-6 sm:py-4 flex items-center justify-end">
							<span class="flex rounded-md shadow-sm">
								<Button
									class="border hover:bg-gray-100"
									@click="showModal = false"
								>
									Cancel
								</Button>
							</span>
							<span class="flex rounded-md shadow-sm ml-3">
								<Button
									class="text-white bg-blue-500 hover:bg-blue-600"
									:disabled="!memberEmail || state === 'Adding Member'"
									@click="addMember(memberEmail)"
								>
									Send Invitation
								</Button>
							</span>
						</div>
					</Modal>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
import Modal from '@/components/Modal';

export default {
	name: 'AccountTeam',
	components: {
		Modal
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
			this.state = 'Adding Member';
			try {
				await this.$call('press.api.account.add_team_member', { team, email });
				this.state = 'Invite Email Sent';
				this.showModal = false;
				this.memberEmail = null;
			} catch (error) {
				this.errorMessage = error.messages.join('\n');
			}
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
