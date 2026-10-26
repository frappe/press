import { createResource } from 'frappe-ui'
import { showErrorToast } from './toast'

// A plain link sends no X-Press-Team header, so a non-owner member gets a 403.
export async function openInvoicePaymentPage(invoiceName) {
	// Open the tab before the request, or the popup blocker stops it.
	const paymentTab = window.open('', '_blank')
	try {
		const response = await createResource({
			url: 'press.api.client.run_doc_method',
		}).submit({ dt: 'Invoice', dn: invoiceName, method: 'stripe_payment_url' })
		if (!response.message) throw new Error('No payment link for this invoice')
		paymentTab.location.href = response.message
	} catch (error) {
		paymentTab.close()
		showErrorToast(error)
	}
}
