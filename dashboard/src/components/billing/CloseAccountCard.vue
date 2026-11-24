<template>
	<div
		v-if="isTeamOwner && team.doc.enabled"
		class="flex items-center justify-between gap-4 border-t pt-6 text-base"
	>
		<div class="flex flex-col gap-1.5">
			<div class="text-lg font-semibold text-ink-gray-9">Close account</div>
			<div class="text-ink-gray-7">
				Disable your account and stop billing. You can enable it again later.
			</div>
		</div>
		<Button
			class="shrink-0"
			label="Close account"
			:route="{ name: 'SettingsProfile', query: { disable: 1 } }"
		/>
	</div>
</template>

<script setup>
import { computed, inject } from 'vue'
import { session } from '../../data/session'

const team = inject('team')
const isTeamOwner = computed(() => team.doc?.user === session.user)
</script>
