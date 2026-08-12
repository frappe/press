import { onMounted, onUnmounted } from 'vue'

export const useRealtimeNotifs = (cb: (data: any) => void) => {
	const socket = window.$socket
	const handler = (data: any) => cb(data)

	onMounted(() => {
		socket.emit('doctype_subscribe', 'Press Notification')
		socket.on('press_notification', handler)
	})

	onUnmounted(() => {
		socket.off('press_notification', handler)
	})
}
