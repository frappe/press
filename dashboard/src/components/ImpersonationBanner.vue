<script setup>
import { computed, inject } from 'vue'
import { getCurrentTeam, isImpersonating } from '@/data/currentTeam'
import { stopImpersonating } from '@/data/team'
import AlertBanner from './AlertBanner.vue'

const team = inject('team')

// Fixed for the life of the tab: leaving the team reloads the page.
const impersonating = isImpersonating()

const title = computed(() => {
	const name = getCurrentTeam()
	const owner = team?.doc?.user
	return `You are on ${owner ? `${owner}'s team, ${name}` : `the team ${name}`}, not your own. Everything you do here is recorded against that team.`
})
</script>

<template>
	<AlertBanner
		v-if="impersonating"
		class="sticky top-0 z-10 m-2 sm:m-4"
		type="warning"
		:title="title"
	>
		<Button class="ml-auto" variant="outline" @click="stopImpersonating">
			Leave team
		</Button>
	</AlertBanner>
</template>
