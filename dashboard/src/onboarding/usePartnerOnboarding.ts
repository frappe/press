import { createResource } from 'frappe-ui'
import { computed, reactive, ref } from 'vue'

type TeamResource = {
	doc?: Record<string, any>
	reload?: () => Promise<void>
}

export type PartnerOnboardingDoc = {
	name?: string
	team?: string
	status?: 'Draft' | 'Submission Pending' | 'Approved' | 'Rejected'
	company_name?: string
	registered_country?: string
	company_email?: string
	contact?: string
	address?: string
	headquarter_city?: string
	annual_revenue?: number | string
	revenue_currency?: string
	employee_range?: string
	certified_employees_range?: string
	verticals_served?: string
	customer_count_range?: string
	erpnext_customer_count_range?: string
	existing_partnerships?: string
	erp_implementations_range?: string
	incorporation_certificate?: string
	agreed_to_due_diligence?: boolean | 0 | 1
	agreed_to_partnership_agreement?: boolean | 0 | 1
}

const doc = ref<PartnerOnboardingDoc | null>(null)
const activeTeam = ref<TeamResource>()

const baseUrl = 'press.partner.doctype.partner_onboarding.partner_onboarding'

const form = reactive<PartnerOnboardingDoc>({
	company_name: '',
	registered_country: '',
	company_email: '',
	contact: '',
	address: '',
	headquarter_city: '',
	annual_revenue: '',
	revenue_currency: 'INR',
	employee_range: '',
	certified_employees_range: '',
	verticals_served: '',
	customer_count_range: '',
	erpnext_customer_count_range: '',
	existing_partnerships: '',
	erp_implementations_range: '',
	incorporation_certificate: '',
	agreed_to_due_diligence: false,
	agreed_to_partnership_agreement: false,
})

function applyDoc(nextDoc: PartnerOnboardingDoc | null, team?: TeamResource) {
	doc.value = nextDoc
	const teamDoc = team?.doc || {}
	Object.assign(form, {
		company_name:
			nextDoc?.company_name ||
			teamDoc.company_name ||
			teamDoc.billing_name ||
			teamDoc.team_title ||
			'',
		registered_country: nextDoc?.registered_country || teamDoc.country || '',
		company_email: nextDoc?.company_email || teamDoc.user || '',
		contact: nextDoc?.contact || teamDoc.phone_number || '',
		address: nextDoc?.address || '',
		headquarter_city: nextDoc?.headquarter_city || '',
		annual_revenue: nextDoc?.annual_revenue || '',
		revenue_currency: nextDoc?.revenue_currency || teamDoc.currency || 'INR',
		employee_range: nextDoc?.employee_range || '',
		certified_employees_range: nextDoc?.certified_employees_range || '',
		verticals_served: nextDoc?.verticals_served || '',
		customer_count_range: nextDoc?.customer_count_range || '',
		erpnext_customer_count_range: nextDoc?.erpnext_customer_count_range || '',
		existing_partnerships: nextDoc?.existing_partnerships || '',
		erp_implementations_range: nextDoc?.erp_implementations_range || '',
		incorporation_certificate: nextDoc?.incorporation_certificate || '',
		agreed_to_due_diligence: Boolean(nextDoc?.agreed_to_due_diligence),
		agreed_to_partnership_agreement: Boolean(
			nextDoc?.agreed_to_partnership_agreement,
		),
	})
}

function detailsFromForm() {
	return {
		...form,
		agreed_to_due_diligence: form.agreed_to_due_diligence ? 1 : 0,
		agreed_to_partnership_agreement: form.agreed_to_partnership_agreement
			? 1
			: 0,
	}
}

const getPartnerOnboarding = createResource({
	url: `${baseUrl}.get_partner_onboarding`,
	auto: false,
	onSuccess: (nextDoc: PartnerOnboardingDoc | null) => {
		applyDoc(nextDoc, activeTeam.value)
	},
})

const savePartnerOnboarding = createResource({
	url: `${baseUrl}.save_partner_onboarding`,
	auto: false,
	onSuccess: (nextDoc: PartnerOnboardingDoc) => {
		applyDoc(nextDoc, activeTeam.value)
	},
})

export function usePartnerOnboarding(team?: TeamResource) {
	activeTeam.value = team

	const isRegistered = computed(() => Boolean(doc.value?.name))
	const isProfileComplete = computed(() =>
		Boolean(
			form.company_name &&
				form.registered_country &&
				form.company_email &&
				form.contact &&
				form.address &&
				form.headquarter_city &&
				form.agreed_to_due_diligence &&
				form.agreed_to_partnership_agreement,
		),
	)
	const loading = computed(() => getPartnerOnboarding.loading)
	const saving = computed(() => savePartnerOnboarding.loading)

	async function load() {
		return getPartnerOnboarding.fetch()
	}

	async function save() {
		return savePartnerOnboarding.submit({
			details: detailsFromForm(),
		})
	}

	return {
		doc,
		form,
		loading,
		saving,
		isRegistered,
		isProfileComplete,
		load,
		save,
	}
}
