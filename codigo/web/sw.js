// Service worker mínimo: permite instalar o Fin Pro como aplicativo.
// Não guarda nada em cache — os dados vêm sempre do servidor local.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (evento) => evento.waitUntil(self.clients.claim()));
