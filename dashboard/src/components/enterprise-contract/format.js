import { currency, date } from '../../utils/format'

export function formatDate(value) {
	return date(value, 'D MMM YYYY')
}

// Contract prices are whole amounts, so they show without decimals.
export function money(amount, currencyCode) {
	return currency(amount, currencyCode, 0)
}

export function gstLines(gst, split) {
	if (split === 'inter_state') return [{ label: 'IGST', amount: gst }]
	if (split !== 'intra_state') return [{ label: 'GST', amount: gst }]
	// SGST takes the odd paisa, so the two lines add up to the GST.
	const cgst = Math.round(gst * 50) / 100
	return [
		{ label: 'CGST', amount: cgst },
		{ label: 'SGST', amount: Math.round((gst - cgst) * 100) / 100 },
	]
}

export function gstText(gst, split, currencyCode) {
	return gstLines(gst, split)
		.map((line) => `${money(line.amount, currencyCode)} ${line.label}`)
		.join(' + ')
}
