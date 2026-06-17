import { createResource } from 'frappe-ui'
import { computed, reactive, ref } from 'vue'

type TeamResource = {
	doc?: Record<string, any>
	reload?: () => Promise<void>
}

export type PartnerLinkedCertificate = {
	name: string
	course: string
	user_email: string
	member_name?: string
}

export type PartnerCertificateLinkRequest = {
	name: string
	course: string
	user_email: string
	status: 'Approved' | 'Cancelled' | 'Pending'
	creation?: string
}

export type PartnerCertificateLinkStatus = {
	linked_certificates: PartnerLinkedCertificate[]
	link_requests: PartnerCertificateLinkRequest[]
	pending_requests: PartnerCertificateLinkRequest[]
	linked_count: number
	requirement_complete: boolean
}

export type PartnerMRRStatus = {
	current_amount: number
	target_amount: number
	currency: string
	progress: number
	requirement_complete: boolean
}

export type PartnerOnboardingDoc = {
	name?: string
	team?: string
	docstatus?: 0 | 1 | 2
	status?: 'Draft' | 'Pending Review' | 'Approved' | 'Rejected' | 'Cancelled'
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
	reviewed_on?: string
	reviewed_by?: string
	reviewer_comments?: string
}

export function getPartnerMRRCurrency(country?: string) {
	if (country === 'India') return 'INR'
	return 'USD'
}

export function getPartnerMRRTargetAmount(currency: string) {
	return currency === 'INR' ? 10000 : 100
}

export function getPartnerMRRTargetLabel(country?: string) {
	const currency = getPartnerMRRCurrency(country)
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency,
		maximumFractionDigits: 0,
	}).format(getPartnerMRRTargetAmount(currency))
}

const doc = ref<PartnerOnboardingDoc | null>(null)
const activeTeam = ref<TeamResource>()
const certificateStatus = ref<PartnerCertificateLinkStatus>({
	linked_certificates: [],
	link_requests: [],
	pending_requests: [],
	linked_count: 0,
	requirement_complete: false,
})
const mrrStatus = ref<PartnerMRRStatus>({
	current_amount: 0,
	target_amount: getPartnerMRRTargetAmount('USD'),
	currency: getPartnerMRRCurrency(),
	progress: 0,
	requirement_complete: false,
})
const certificateStatusResources = new Map<string, any>()
const mrrStatusResources = new Map<string, any>()

const baseUrl = 'press.partner.doctype.partner_onboarding.partner_onboarding'
const certificateTypeCourses: Record<string, string[]> = {
	frappe: [
		'frappe-developer-certification',
		'app-development-with-frappe-framework',
	],
	erpnext: ['erpnext-distribution', 'erpnext-training'],
}

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

function resetCertificateStatus() {
	certificateStatus.value = {
		linked_certificates: [],
		link_requests: [],
		pending_requests: [],
		linked_count: 0,
		requirement_complete: false,
	}
}

function resetMRRStatus() {
	mrrStatus.value = {
		current_amount: 0,
		target_amount: getPartnerMRRTargetAmount('USD'),
		currency: getPartnerMRRCurrency(),
		progress: 0,
		requirement_complete: false,
	}
}

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

function getTeamName(team?: TeamResource) {
	return (
		team?.doc?.name ||
		localStorage.getItem('current_team') ||
		(window as any).default_team ||
		''
	)
}

function getCertificateStatusResource(team?: TeamResource) {
	const teamName = getTeamName(team)
	const cacheKey = `partner_onboarding_certificates:${teamName}`

	if (!certificateStatusResources.has(cacheKey)) {
		certificateStatusResources.set(
			cacheKey,
			createResource({
				url: `${baseUrl}.get_certificate_link_status`,
				cache: cacheKey,
				auto: false,
				onSuccess: (status: PartnerCertificateLinkStatus) => {
					certificateStatus.value = status
				},
			}),
		)
	}

	return certificateStatusResources.get(cacheKey)
}

function getMRRStatusResource(team?: TeamResource) {
	const teamName = getTeamName(team)
	const cacheKey = `partner_onboarding_mrr:${teamName}`

	if (!mrrStatusResources.has(cacheKey)) {
		mrrStatusResources.set(
			cacheKey,
			createResource({
				url: `${baseUrl}.get_mrr_status`,
				cache: cacheKey,
				auto: false,
				onSuccess: (status: PartnerMRRStatus) => {
					mrrStatus.value = status
				},
			}),
		)
	}

	return mrrStatusResources.get(cacheKey)
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
		const wasRegistered = Boolean(doc.value?.name)
		applyDoc(nextDoc, activeTeam.value)
		// First registration only needs the sidebar to surface the "Partnership"
		// item (see NavList.vue / Sidebar.vue). The backend doesn't mutate the
		// Team here — the sole delta is the computed `has_partner_onboarding`
		// flag — so set it optimistically instead of triggering a heavy full
		// Team reload (balance, billing, subscriptions, ...).
		if (!wasRegistered && nextDoc?.name && activeTeam.value?.doc) {
			activeTeam.value.doc.has_partner_onboarding = true
		}
	},
})

const submitPartnerOnboarding = createResource({
	url: `${baseUrl}.submit_for_approval`,
	auto: false,
	onSuccess: (nextDoc: PartnerOnboardingDoc) => {
		applyDoc(nextDoc, activeTeam.value)
	},
})

const unregisterPartnerOnboarding = createResource({
	url: `${baseUrl}.unregister`,
	auto: false,
	onSuccess: () => {
		applyDoc(null, activeTeam.value)
		resetCertificateStatus()
		resetMRRStatus()
		// Record removed — reload the team so the sidebar drops "Partnership"
		// and the "Become a Partner" entry returns to the dropdown.
		void activeTeam.value?.reload?.()
	},
})

export function usePartnerOnboarding(team?: TeamResource) {
	activeTeam.value = team
	const certificateStatusResource = getCertificateStatusResource(team)
	const mrrStatusResource = getMRRStatusResource(team)

	const isRegistered = computed(() => Boolean(doc.value?.name))
	const isProfileComplete = computed(() =>
		Boolean(
			form.company_name &&
				form.registered_country &&
				form.company_email &&
				form.contact &&
				form.address &&
				form.headquarter_city &&
				form.incorporation_certificate &&
				form.agreed_to_due_diligence &&
				form.agreed_to_partnership_agreement,
		),
	)
	const loading = computed(() => getPartnerOnboarding.loading)
	const saving = computed(() => savePartnerOnboarding.loading)
	const submittingForApproval = computed(() => submitPartnerOnboarding.loading)
	const unregistering = computed(() => unregisterPartnerOnboarding.loading)
	const certificateLoading = computed(() => certificateStatusResource.loading)
	const linkedCertificateCount = computed(
		() => certificateStatus.value.linked_count || 0,
	)
	const hasCertificateActivity = computed(
		() =>
			isRegistered.value &&
			(linkedCertificateCount.value > 0 ||
				(certificateStatus.value.link_requests?.length || 0) > 0),
	)
	const isCertificateRequirementComplete = computed(
		() => certificateStatus.value.requirement_complete,
	)
	const isMRRRequirementComplete = computed(
		() => mrrStatus.value.requirement_complete,
	)

	async function load() {
		const nextDoc = await getPartnerOnboarding.fetch()
		if (!nextDoc) {
			resetCertificateStatus()
			resetMRRStatus()
			return nextDoc
		}
		// Certificate and MRR status are independent — fetch them concurrently so
		// the partner-onboarding page renders without waiting on a serial chain.
		await Promise.all([loadCertificateStatus(), loadMRRStatus()])
		return nextDoc
	}

	async function loadPartnerOnboarding() {
		if (getPartnerOnboarding.reload) {
			return getPartnerOnboarding.reload()
		}
		return getPartnerOnboarding.fetch()
	}

	async function save() {
		return savePartnerOnboarding.submit({
			details: detailsFromForm(),
		})
	}

	async function submitForApproval() {
		return submitPartnerOnboarding.submit()
	}

	async function unregister() {
		return unregisterPartnerOnboarding.submit()
	}

	async function loadCertificateStatus() {
		if (!isRegistered.value) {
			resetCertificateStatus()
			return certificateStatus.value
		}
		if (certificateStatusResource.reload) {
			return certificateStatusResource.reload()
		}
		return certificateStatusResource.fetch()
	}

	async function loadMRRStatus() {
		if (mrrStatusResource.reload) {
			return mrrStatusResource.reload()
		}
		return mrrStatusResource.fetch()
	}

	async function sendCertificateLinkRequest(params: {
		user_email: string
		certificate_type: string
	}) {
		const resource = createResource({
			url: `${baseUrl}.send_certificate_link_request`,
			auto: false,
		})
		const result = await resource.submit(params)
		await loadCertificateStatus()
		return result
	}

	async function resendCertificateLinkRequest(requestName: string) {
		const resource = createResource({
			url: `${baseUrl}.resend_certificate_link_request`,
			auto: false,
		})
		const result = await resource.submit({ request_name: requestName })
		await loadCertificateStatus()
		return result
	}

	function hasPendingCertificateRequest(
		userEmail: string,
		certificateType: string,
	) {
		const normalizedEmail = userEmail.trim().toLowerCase()
		const courses = certificateTypeCourses[certificateType] || []

		return Boolean(
			certificateStatus.value.pending_requests?.some(
				(request) =>
					request.user_email.toLowerCase() === normalizedEmail &&
					courses.includes(request.course),
			),
		)
	}

	return {
		doc,
		form,
		certificateStatus,
		mrrStatus,
		loading,
		saving,
		submittingForApproval,
		unregistering,
		certificateLoading,
		isRegistered,
		isProfileComplete,
		linkedCertificateCount,
		hasCertificateActivity,
		isCertificateRequirementComplete,
		isMRRRequirementComplete,
		load,
		save,
		submitForApproval,
		unregister,
		loadPartnerOnboarding,
		loadCertificateStatus,
		loadMRRStatus,
		sendCertificateLinkRequest,
		resendCertificateLinkRequest,
		hasPendingCertificateRequest,
	}
}
