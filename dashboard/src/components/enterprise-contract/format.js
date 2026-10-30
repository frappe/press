import { currency, date } from '../../utils/format'

export function formatDate(value) {
	return date(value, 'D MMM YYYY')
}

// Contract prices are whole amounts, so they show without decimals.
export function money(amount, currencyCode) {
	return currency(amount, currencyCode, 0)
}
