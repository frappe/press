import { unparse } from 'papaparse'

export function downloadCSV(rows, filename) {
	if (!rows.length) return

	// Byte order mark, so Excel reads it as UTF-8
	const csv = '\uFEFF' + unparse(rows)
	const link = document.createElement('a')
	link.href = URL.createObjectURL(
		new Blob([csv], { type: 'text/csv;charset=utf-8' }),
	)
	link.download = filename
	link.click()
	URL.revokeObjectURL(link.href)
}
