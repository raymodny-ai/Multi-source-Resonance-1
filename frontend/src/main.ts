import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import wsClient from './api/websocket'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.mount('#app')

// ponytail: WebSocket is the primary live-update channel; REST polling is the
// fallback. Stores subscribe to topics in their own setup; we just need to
// open the socket once at app boot.
wsClient.connect()
