<template>
	<Dialog :options="{ title: 'Change Team' }" v-model="show">
		<template #body-content>
			<div class="rounded bg-gray-100 px-3 py-2.5">
				<div class="text-base text-gray-900">
					You are logged in as
					<span class="font-medium">{{ $session.user }}</span>
				</div>
				<div class="mt-2 text-base text-gray-900">
					You are viewing dashboard for
					<span class="font-medium">{{ $team.doc.user }}</span>
					<span
						class="font-mono text-sm text-gray-500"
						v-if="$team.name != $team.doc.user"
					>
						({{ $team.name }})
					</span>
				</div>
			</div>
			<div class="-mb-3 mt-3 divide-y">
				<div
					class="flex items-center justify-between py-3"
					v-for="team in $team.doc.valid_teams"
					:key="team.name"
				>
					<div>
						<span class="text-base text-gray-800">
							{{ team.user }}
						</span>
						<span
							class="font-mono text-sm text-gray-500"
							v-if="team.name != team.user"
						>
							({{ team.name }})
						</span>
					</div>
					<Badge
						class="whitespace-nowrap"
						v-if="$team.name === team.name"
						label="Currently Active"
						theme="green"
					/>
					<Button v-else @click="switchToTeam(team.name)">Change</Button>
				</div>
			</div>
			<div class="mt-6 flex items-end gap-2" v-if="$session.isSystemUser">
				<LinkControl
					class="w-full"
					label="Select Team"
					:options="{ doctype: 'Team', filters: { enabled: 1 } }"
					v-model="selectedTeam"
					description="This feature is only available to system users"
				/>
				<div class="pb-5">
					<Button :disabled="!selectedTeam" @click="switchToTeam(selectedTeam)">
						Change
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { switchToTeam } from '../data/team';
import LinkControl from './LinkControl.vue';

export default {
	name: 'SwitchTeamDialog',
	props: ['modelValue'],
	emits: ['update:modelValue'],
	components: { LinkControl },
	computed: {
		show: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		}
	},
	data() {
		return {
			selectedTeam: null
		};
	},
	methods: {
		switchToTeam
	}
};
</script>
