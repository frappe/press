// English letters and digits, plus characters common in billing names:
// hyphen, apostrophe, comma, period, parentheses, ampersand, plus, slash
// (M/s, S/o) and spaces.
const billingNameRegex = /^[a-zA-Z0-9',.()&+/\s-]+$/

export function validateBillingName(billingName) {
	const trimmedName = (billingName || '').trim()
	if (!trimmedName) return ''
	return billingNameRegex.test(trimmedName) ? trimmedName : null
}

export const indianStates = [
	'Andaman and Nicobar Islands',
	'Andhra Pradesh',
	'Arunachal Pradesh',
	'Assam',
	'Bihar',
	'Chandigarh',
	'Chhattisgarh',
	'Dadra and Nagar Haveli and Daman and Diu',
	'Delhi',
	'Goa',
	'Gujarat',
	'Haryana',
	'Himachal Pradesh',
	'Jammu and Kashmir',
	'Jharkhand',
	'Karnataka',
	'Kerala',
	'Ladakh',
	'Lakshadweep Islands',
	'Madhya Pradesh',
	'Maharashtra',
	'Manipur',
	'Meghalaya',
	'Mizoram',
	'Nagaland',
	'Odisha',
	'Other Territory',
	'Puducherry',
	'Punjab',
	'Rajasthan',
	'Sikkim',
	'Tamil Nadu',
	'Telangana',
	'Tripura',
	'Uttar Pradesh',
	'Uttarakhand',
	'West Bengal',
]
