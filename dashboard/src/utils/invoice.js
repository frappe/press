import { createResource } from 'frappe-ui'
import { openInNewTab } from './site'
import { showErrorToast } from './toast'

export function openInvoicePaymentPage(invoiceName) {
	openInNewTab(fetchPaymentUrl(invoiceName), 'Opening payment page…').catch(
		showErrorToast,
	)
}

// A plain link sends no X-Press-Team header, so a non-owner member gets a 403.
async function fetchPaymentUrl(invoiceName) {
	const response = await createResource({
		url: 'press.api.client.run_doc_method',
	}).submit({ dt: 'Invoice', dn: invoiceName, method: 'stripe_payment_url' })
	if (!response.message) {
		throw new Error(
			'This invoice has no Stripe payment link. Contact support to pay it.',
		)
	}
	return response.message
}
