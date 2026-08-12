import { onMounted, onUnmounted } from 'vue'

type SocketHandler<T = any> = (data: T) => void

export function useSocketEvent<T = any>(
	event: string,
	handler: SocketHandler<T>,
) {
	let socket: any

	onMounted(() => {
		socket = (window as any).$socket
		if (!socket) {
			console.warn('Socket is not enabled.')
			return
		}

		socket.on(event, handler)
	})

	onUnmounted(() => {
		if (!socket) return

		socket.off(event, handler)
	})
}
