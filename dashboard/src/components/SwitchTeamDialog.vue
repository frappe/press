<template>
	<Dialog :options="{ title: 'Switch Team' }" v-model="show">
		<template #body-content v-if="$team?.doc">
			<div class="rounded bg-gray-100 px-3 py-2.5">
				<div class="text-base text-gray-900">
					Signed in as
					<span class="font-medium">{{ $session.user }}</span>
				</div>
				<div class="mt-1.5 text-base text-gray-900">
					Viewing dashboard for the team
					<component
						:is="$team.doc.is_desk_user ? 'a' : 'span'"
						class="font-medium"
						:class="{ underline: $team.doc.is_desk_user }"
						:href="$team.doc.is_desk_user ? `/app/team/${$team.name}` : null"
						target="_blank"
					>
						{{ $team.doc.user }}
					</component>
				</div>
			</div>
			<div class="mt-4">
				<TextInput
					ref="searchRef"
					size="sm"
					placeholder="Search"
					:debounce="500"
					v-model="searchQuery"
				>
					<template #suffix>
						<lucide-search class="h-4 w-4 text-gray-500" />
					</template>
				</TextInput>
			</div>
			<div class="-mb-3 mt-3 divide-y">
				<div
					class="flex items-center justify-between py-3"
					v-for="team in filteredTeams"
					:key="team.name"
				>
					<div class="flex items-center space-x-2 px-0.5">
						<span class="text-base text-gray-800">
							{{ team.user }}
						</span>
						<Button
							v-if="$team.doc.is_desk_user"
							icon="external-link"
							:link="`/app/team/${team.name}`"
							variant="ghost"
							size="sm"
						/>
						<Badge
							class="whitespace-nowrap"
							v-if="team.user === $session.user"
							label="Your team"
							theme="blue"
							size="md"
						/>
					</div>
					<Badge
						class="whitespace-nowrap"
						v-if="$team.name === team.name"
						size="md"
						label="Active"
						theme="green"
					/>
					<Button v-else @click="switchToTeam(team.name)" size="sm"
						>Switch</Button
					>
				</div>
			</div>
			<div class="mt-6 flex items-center gap-2" v-if="$session.isSystemUser">
				<LinkControl
					class="w-full"
					label="Select team"
					:options="{ doctype: 'Team', filters: { enabled: 1 } }"
					v-model="selectedTeam"
					description="This feature is only available to system users"
				/>
				<div class="mb-1">
					<Button
						:disabled="!selectedTeam"
						@click="switchToTeam(selectedTeam)"
						size="sm"
					>
						Switch
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { TextInput } from 'frappe-ui';
import { switchToTeam } from '../data/team';
import LinkControl from './LinkControl.vue';

export default {
	name: 'SwitchTeamDialog',
	props: ['modelValue'],
	emits: ['update:modelValue'],
	components: { LinkControl, TextInput },
	computed: {
		show: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			},
		},
		sortedTeams() {
			const validTeams = this.$team?.doc?.valid_teams;
			if (!validTeams) return [];

			const sorted = [...validTeams].sort((a, b) => {
				return a.user.localeCompare(b.user);
			});

			return [
				...sorted.filter((team) => team.user === this.$session.user),
				...sorted.filter((team) => team.user !== this.$session.user),
			];
		},
		filteredTeams() {
			if (!this.searchQuery.trim()) {
				return this.sortedTeams;
			}
			const query = this.searchQuery.toLowerCase();
			return this.sortedTeams.filter(
				(team) =>
					team.user.toLowerCase().includes(query) ||
					team.name.toLowerCase().includes(query),
			);
		},
	},
	data() {
		return {
			selectedTeam: null,
			searchQuery: '',
		};
	},
	methods: {
		switchToTeam,
	},
	mounted() {
		setTimeout(() => {
			const textInput = this.$refs.searchRef?.$el;
			const inputHtmlElement = textInput?.querySelector('input');
			inputHtmlElement?.focus();
		}, 200);
	},
};
</script>
