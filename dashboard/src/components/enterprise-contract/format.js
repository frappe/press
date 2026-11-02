import { currency, date } from '../../utils/format'
import { getSiteStatusBadge } from '../../utils/site'

export function formatDate(value) {
	return date(value, 'D MMM YYYY')
}

// Contract prices are whole amounts, so they show without decimals.
export function money(amount, currencyCode) {
	return currency(amount, currencyCode, 0)
}

export function contractStatusBadge(status) {
	return getSiteStatusBadge(status === 'Pending Signature' ? 'Draft' : status)
}

export function gstLines(gst, split) {
	if (split === 'inter_state') return [{ label: 'IGST', amount: gst }]
	if (split !== 'intra_state') return [{ label: 'GST', amount: gst }]
	// SGST is the remainder, so the two lines add up to the GST.
	const cgst = Math.round(gst * 50) / 100
	return [
		{ label: 'CGST', amount: cgst },
		{ label: 'SGST', amount: Math.round((gst - cgst) * 100) / 100 },
	]
}

export function gstText(gst, split, currencyCode) {
	return gstLines(gst, split)
		.map((line) => {
			// A half can end in paise; rounding it would break the sum.
			const digits = Number.isInteger(line.amount) ? 0 : 2
			return `${currency(line.amount, currencyCode, digits)} ${line.label}`
		})
		.join(' + ')
}
