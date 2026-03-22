// Deshabilitar SSR globalmente: los tokens están en localStorage (no accesible en Node SSR).
// Para una app personal en Docker local esto es apropiado.
export const ssr = false;
