<script setup lang="ts">
import { Button, Checkbox, FileUploader, FormControl, Tooltip } from 'frappe-ui'
import { computed, ref } from 'vue'
import type { PartnerOnboardingDoc } from '@/onboarding/usePartnerOnboarding'
import LucideHelpCircle from '~icons/lucide/help-circle'

const emit = defineEmits(['continue'])
const props = defineProps<{
	form: PartnerOnboardingDoc
}>()
const submitted = ref(false)

// ideally this should be multi select.
// cspell:ignore Odoo
const partnershipOptions = [
	{ label: 'SAP', value: 'SAP' },
	{ label: 'Odoo', value: 'Odoo' },
	{ label: 'Oracle', value: 'Oracle' },
	{ label: 'Microsoft', value: 'Microsoft' },
]

const implementationOptions = [
	{ label: '1-10', value: '1-10' },
	{ label: '11-50', value: '11-50' },
	{ label: '51-200', value: '51-200' },
	{ label: '201+', value: '201+' },
]

const errors = computed(() => {
	if (!submitted.value) return {}
	return {
		incorporation_certificate: !props.form.incorporation_certificate,
		due_diligence: !props.form.agreed_to_due_diligence,
		partnership_agreement: !props.form.agreed_to_partnership_agreement,
		company_logo: !props.form.company_logo,
	}
})

const PARTNERSHIP_AGREEMENT_LINK = 'https://frappe.io/partners/terms'
const documentFileTypes = ['application/pdf', 'image/*']
const logoFileTypes = ['image/*']
const incorporationCertificateHelp =
	'Upload your certificate of incorporation or equivalent company registration document. This helps us verify your legal entity before partnership approval.'

const companyLogoHelp =
	'Upload your company logo. This will be displayed on the partner listing — use a square image that is not too large.'

function validateDocument(file: File) {
	const allowedType =
		file.type === 'application/pdf' || file.type.startsWith('image/')
	if (!allowedType) return 'Upload a PDF or image file.'
	if (file.size > 10 * 1024 * 1024) return 'File size must be under 10 MB.'
	return null
}

function validateLogo(file: File) {
	if (!file.type.startsWith('image/')) return 'Upload an image file.'
	if (file.size > 5 * 1024 * 1024) return 'Logo must be under 5 MB.'
	return null
}

function onCertificateUploadSuccess(file: { file_url?: string }) {
	props.form.incorporation_certificate = file.file_url || ''
}

function onLogoUploadSuccess(file: { file_url?: string }) {
	props.form.company_logo = file.file_url || ''
}

function validate() {
	submitted.value = true
	return !Object.values(errors.value).some(Boolean)
}

function tryContinue() {
	if (validate()) emit('continue')
}

defineExpose({ tryContinue })
</script>

<template>
	<form
		id="company-information-form-3"
		class="flex min-h-[360px] flex-col gap-5"
		@submit.prevent="tryContinue"
	>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-ink-gray-6">Existing Partnerships</span>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<FormControl
					v-model="props.form.existing_partnerships"
					type="select"
					size="sm"
					variant="outline"
					placeholder="Select"
					:options="partnershipOptions"
				/>
			</div>

			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-ink-gray-6"
						>No. of ERP implementations</span
					>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<FormControl
					v-model="props.form.erp_implementations_range"
					type="select"
					size="sm"
					variant="outline"
					placeholder="Select"
					:options="implementationOptions"
				/>
			</div>
		</div>

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<div class="flex items-center gap-1">
						<span class="text-xs text-ink-gray-6">Company logo</span>
						<Tooltip :text="companyLogoHelp">
							<LucideHelpCircle class="size-3 text-ink-gray-5" />
						</Tooltip>
					</div>
				</div>
				<FileUploader
					:fileTypes="logoFileTypes"
					:validateFile="validateLogo"
					:uploadArgs="{ private: false }"
					@success="onLogoUploadSuccess"
				>
					<template #default="{ uploading, progress, openFileSelector, error }">
						<Button
							variant="outline"
							class="w-full justify-start"
							:loading="uploading"
							@click="openFileSelector"
						>
							{{ uploading
									? `Uploading ${progress}%`
									: props.form.company_logo
										? 'Replace logo'
										: 'Upload logo' }}
						</Button>
						<p
							v-if="props.form.company_logo"
							class="mt-1 truncate text-xs text-ink-gray-6"
						>
							{{ props.form.company_logo }}
						</p>
						<p v-if="error" class="mt-1 text-sm text-ink-red-4">
							{{ error }}
						</p>
					</template>
				</FileUploader>
				<p v-if="errors.company_logo" class="text-sm text-ink-red-4">
					Company logo is required.
				</p>
			</div>

			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<div class="flex items-center gap-1">
						<span class="text-xs text-ink-gray-6"
							>Incorporation certificate</span
						>
						<Tooltip :text="incorporationCertificateHelp">
							<LucideHelpCircle class="size-3 text-ink-gray-5" />
						</Tooltip>
					</div>
				</div>
				<FileUploader
					:fileTypes="documentFileTypes"
					:validateFile="validateDocument"
					:uploadArgs="{ private: true }"
					@success="onCertificateUploadSuccess"
				>
					<template #default="{ uploading, progress, openFileSelector, error }">
						<Button
							variant="outline"
							class="w-full justify-start"
							:loading="uploading"
							@click="openFileSelector"
						>
							{{ uploading
									? `Uploading ${progress}%`
									: props.form.incorporation_certificate
										? 'Replace document'
										: 'Attach document' }}
						</Button>
						<p
							v-if="props.form.incorporation_certificate"
							class="mt-1 truncate text-xs text-ink-gray-6"
						>
							{{ props.form.incorporation_certificate }}
						</p>
						<p v-if="error" class="mt-1 text-sm text-ink-red-4">
							{{ error }}
						</p>
					</template>
				</FileUploader>
				<p
					v-if="errors.incorporation_certificate"
					class="text-sm text-ink-red-4"
				>
					Incorporation certificate is required.
				</p>
			</div>
		</div>

		<div class="mt-1 flex flex-col gap-3">
			<Checkbox
				v-model="props.form.agreed_to_due_diligence"
				label="I shall abide by the due diligence"
			/>
			<p v-if="errors.due_diligence" class="-mt-2 text-sm text-ink-red-4">
				Due diligence confirmation is required.
			</p>

			<div class="flex items-start gap-2">
				<Checkbox
					v-model="props.form.agreed_to_partnership_agreement"
					id="partnership-agreement-checkbox"
				/>
				<label
					for="partnership-agreement-checkbox"
					class="text-base font-medium text-ink-gray-8"
				>
					I accept the
					<a
						:href="PARTNERSHIP_AGREEMENT_LINK"
						target="_blank"
						rel="noopener noreferrer"
						class="underline"
					>
						Partnership agreement
					</a>
				</label>
			</div>
			<p
				v-if="errors.partnership_agreement"
				class="-mt-2 text-sm text-ink-red-4"
			>
				Partnership agreement acceptance is required.
			</p>
		</div>
	</form>
</template>
