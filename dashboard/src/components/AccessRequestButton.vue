<template>
	<Button
		v-if="show"
		v-bind="buttonProps"
		variant="subtle"
		@click="openDialog"
	/>
</template>

<script setup lang="ts">
import { createResource } from 'frappe-ui'
import { computed, h, ref, watch } from 'vue'
import { getTeam } from '../data/team'
import { renderDialog } from '../utils/components'
import AccessRequestDialog from './AccessRequestDialog.vue'
import AccessRequestStatusDialog, {
	type Access,
} from './AccessRequestStatusDialog.vue'

const props = defineProps<{
	doctype: string
	docname: string
	doc?: any
	error?: Error
}>()

const team = getTeam()

const canRequestAccess = computed(() => {
	return Boolean(team.doc?.can_request_access)
})

const isPermissionError = computed(() => {
	return Boolean(props.error?.message.endsWith('PermissionError'))
})

// Employees read documents of other teams without a grant, so a loaded document proves nothing.
const readsOtherTeam = computed(() => {
	return Boolean(props.doc) && props.doc.team !== team.doc?.name
})

const status = createResource({ url: 'press.api.access.status' })

// The active grant on this document, null when there is none, undefined before the check.
const grant = ref<Access | null | undefined>(undefined)
let latestCheck = 0

async function fetchGrant(): Promise<Access | null> {
	try {
		return await status.fetch({
			doctype: props.doctype,
			docname: props.docname,
		})
	} catch {
		// The endpoint answers "no grant" with a PermissionError.
		return null
	}
}

// The counter drops the answer of a check that a newer document replaced.
async function checkGrant() {
	const check = ++latestCheck
	grant.value = undefined
	if (!canRequestAccess.value || !readsOtherTeam.value) return
	const result = await fetchGrant()
	if (check === latestCheck) grant.value = result
}

watch(
	[canRequestAccess, readsOtherTeam, () => props.doctype, () => props.docname],
	checkGrant,
	{ immediate: true },
)

const hasGrant = computed(() => Boolean(grant.value))

const grantChecked = computed(() => grant.value !== undefined)

const show = computed(() => {
	return (
		canRequestAccess.value &&
		(isPermissionError.value || (readsOtherTeam.value && grantChecked.value))
	)
})

const buttonProps = computed(() => {
	if (hasGrant.value) {
		return { label: '', icon: 'unlock' }
	}
	return { label: 'Request Access', iconLeft: 'lock' }
})

function openRequestDialog() {
	renderDialog(
		h(AccessRequestDialog, {
			doctype: props.doctype,
			docname: props.docname,
		}),
	)
}

function openDialog() {
	const access = grant.value
	if (!access) {
		openRequestDialog()
		return
	}
	renderDialog(
		h(AccessRequestStatusDialog, {
			doctype: props.doctype,
			docname: props.docname,
			access,
			onOpenRequestDialog: openRequestDialog,
		}),
	)
}
</script>
