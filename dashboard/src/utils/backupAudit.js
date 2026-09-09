import { bytes, date } from './format'

// A day nothing could answer for reads as no backup, unless the server never answered
export function statusLabel(row, unconfirmed) {
	if (row.status === 'Not Available') {
		return unconfirmed ? 'Unconfirmed' : 'No backup'
	}
	return row.status === 'Failure' ? 'Failed' : row.status
}

export function statusTheme(label) {
	return (
		{ Success: 'green', Failed: 'red', Unconfirmed: 'orange' }[label] || 'gray'
	)
}

export function filesTheme(files) {
	return { Stored: 'green', Unknown: 'orange' }[files] || 'gray'
}

export function filesDetail(row) {
	if (row.files === 'Stored') {
		return row.keep_till
			? `${row.rule} copy · kept till ${date(row.keep_till, 'll')}`
			: `${row.rule || ''} copy`.trim()
	}
	if (row.files === 'Deleted') {
		if (!row.expired_on) return 'Deletion date not recorded'
		const rule = row.rule ? ` · ${row.rule.toLowerCase()} expiry` : ''
		return `${date(row.expired_on, 'll')}${rule}`
	}
	if (row.files === 'Unknown') return "The server didn't say"
	return row.status === 'Failure' ? 'Nothing was stored' : ''
}

// A blank size cell used to mean four different things, so every cell says which
export function sizeLabel(row, value) {
	if (row.status !== 'Success') return '—'
	if (!row.sizes_known) return 'Not recorded'
	return value ? bytes(value) : '—'
}

// The number is on record, the object it describes is gone
export function sizeIsFromRecord(row) {
	return row.sizes_known && row.files !== 'Stored'
}

export function backupType(row) {
	if (row.offsite === null) return ''
	const parts = [row.physical ? 'Physical' : 'Logical']
	if (row.offsite) parts.push('offsite')
	if (row.with_files) parts.push('with files')
	return parts.join(', ')
}

export function totalSize(row) {
	if (!row.sizes_known) return ''
	const total = row.database + row.public + row.private + row.config
	return total ? bytes(total) : ''
}
