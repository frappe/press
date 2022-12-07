import dayjs from 'dayjs'
import relativeTime from 'dayjs/esm/plugin/relativeTime'
import localizedFormat from 'dayjs/plugin/localizedFormat'
import updateLocale from 'dayjs/plugin/updateLocale'
import isToday from 'dayjs/plugin/isToday'

dayjs.extend(updateLocale)
dayjs.extend(relativeTime)
dayjs.extend(localizedFormat)
dayjs.extend(isToday)

dayjs.shortFormating = (s, ago = false) => {
	if (s === "now" || s === "now ago") {
		return "now"
	}

	const prefix = s.split(" ")[0]
	const posfix = s.split(" ")[1]
	const isPast = s.includes("ago")
	let newPostfix = ""
	switch (posfix) {
		case "minute":
			newPostfix = "m"
			break
		case "minutes":
			newPostfix = "m"
			break
		case "hour":
			newPostfix = "h"
			break
		case "hours":
			newPostfix = "h"
			break
		case "day":
			newPostfix = "d"
			break
		case "days":
			newPostfix = "d"
			break
		case "month":
			newPostfix = "M"
			break
		case "months":
			newPostfix = "M"
			break
		case "year":
			newPostfix = "Y"
			break
		case "years":
			newPostfix = "Y"
			break
	}
	return `${prefix} ${newPostfix}${isPast ? (ago ? " ago" : "") : ""}`
}

export default dayjs