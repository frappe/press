export interface NavItemProps {
	name?: string
	icon?: any
	route?: string
	is?: string
	condition?: boolean
	disabled?: boolean
	isActive?: boolean
	prefix?: any
	suffix?: any
	onClick?: () => void
	css?: string
}
