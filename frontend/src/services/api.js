// Toda la comunicación con Django pasa por este archivo.
// Para cambiar el servidor, configura VITE_API_URL en el archivo .env.
export const API_URL = (import.meta.env?.VITE_API_URL || 'http://127.0.0.1:8000/api').replace(
  /\/$/,
  ''
);
export const ADMIN_URL = `${API_URL.replace(/\/api$/, '')}/admin/`;
const STORAGE_KEY = 'reservas.sesion';

export function obtenerTokens() {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY)) || null;
  } catch {
    sessionStorage.removeItem(STORAGE_KEY);
    return null;
  }
}
export function guardarTokens(tokens) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
}
export function borrarTokens() {
  sessionStorage.removeItem(STORAGE_KEY);
}

const nombresCampos = {
  username: 'Usuario',
  email: 'Correo',
  password: 'Contraseña',
  password_confirmacion: 'Confirmación',
  first_name: 'Nombres',
  last_name: 'Apellidos',
  cedula: 'Cédula',
  telefono: 'Teléfono',
  non_field_errors: '',
  detail: '',
  inicio: 'Inicio',
  fin: 'Fin',
};

// Convierte los errores de validación de Django en mensajes legibles.
function mensajeError(datos) {
  if (typeof datos === 'string') return datos;
  if (Array.isArray(datos)) return datos.map(mensajeError).join(' ');
  if (datos && typeof datos === 'object')
    return Object.entries(datos)
      .map(([campo, valor]) => {
        const etiqueta = nombresCampos[campo] ?? campo;
        return `${etiqueta ? `${etiqueta}: ` : ''}${mensajeError(valor)}`;
      })
      .join(' ');
  return 'No se pudo completar la solicitud.';
}

async function leerRespuesta(respuesta) {
  const contenido = await respuesta.text();
  if (!contenido) return null;
  try {
    return JSON.parse(contenido);
  } catch {
    return {
      detail:
        'El servidor no devolvió una respuesta válida. Comprueba que Django esté ejecutándose.',
    };
  }
}

let renovacionPendiente = null;
async function renovarAcceso() {
  // Varias consultas pueden vencer juntas: se comparte una única renovación.
  if (!renovacionPendiente) {
    const anteriores = obtenerTokens();
    renovacionPendiente = (async () => {
      if (!anteriores?.refresh) return false;
      const respuesta = await fetch(`${API_URL}/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: anteriores.refresh }),
      });
      if (!respuesta.ok) return false;
      const nuevos = await respuesta.json();
      if (obtenerTokens()?.refresh !== anteriores.refresh) return false;
      guardarTokens({ ...anteriores, ...nuevos });
      return true;
    })().finally(() => {
      renovacionPendiente = null;
    });
  }
  return renovacionPendiente;
}

export async function solicitar(
  ruta,
  { method = 'GET', body, autenticado = true, reintentar = true } = {}
) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const tokens = obtenerTokens();
  if (autenticado && tokens?.access) headers.Authorization = `Bearer ${tokens.access}`;
  let respuesta;
  try {
    respuesta = await fetch(`${API_URL}${ruta}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (respuesta.status === 401 && autenticado && reintentar && (await renovarAcceso())) {
      return solicitar(ruta, { method, body, autenticado, reintentar: false });
    }
  } catch {
    throw new Error(
      'No se pudo conectar con el servidor. Comprueba tu conexión y que Django esté ejecutándose.'
    );
  }
  const datos = await leerRespuesta(respuesta);
  if (!respuesta.ok) {
    if (respuesta.status === 401 && autenticado) {
      borrarTokens();
      window.dispatchEvent(new Event('sesion-vencida'));
    }
    throw new Error(mensajeError(datos));
  }
  return datos;
}

function consulta(parametros = {}) {
  const valores = Object.entries(parametros).filter(
    ([, valor]) => valor !== '' && valor !== undefined && valor !== null
  );
  const texto = new URLSearchParams(valores).toString();
  return texto ? `?${texto}` : '';
}

// Cada función representa una operación del backend y mantiene las URLs fuera de las páginas.
export const cuentasApi = {
  login: (datos) => solicitar('/token/', { method: 'POST', body: datos, autenticado: false }),
  registro: (datos) =>
    solicitar('/cuentas/registro/', { method: 'POST', body: datos, autenticado: false }),
  perfil: () => solicitar('/cuentas/perfil/'),
  guardarPerfil: (datos) => solicitar('/cuentas/perfil/', { method: 'PATCH', body: datos }),
};
export const catalogoApi = {
  complejos: (filtros) => solicitar(`/complejos/${consulta(filtros)}`),
  complejo: (id) => solicitar(`/complejos/${id}/`),
  cancha: (id) => solicitar(`/canchas/${id}/`),
  disponibilidad: (id, filtros) => solicitar(`/canchas/${id}/disponibilidad/${consulta(filtros)}`),
};
export const reservasApi = {
  listar: () => solicitar('/reservas/'),
  detalle: (id) => solicitar(`/reservas/${id}/`),
  cotizar: (datos) => solicitar('/reservas/cotizar/', { method: 'POST', body: datos }),
  confirmar: (datos) => solicitar('/reservas/', { method: 'POST', body: datos }),
  cancelar: (id, motivo) =>
    solicitar(`/reservas/${id}/cancelar/`, { method: 'POST', body: { motivo } }),
};
export const encuestasApi = {
  pendientes: () => solicitar('/encuestas/pendientes/'),
  responder: (id, datos) =>
    solicitar(`/encuestas/${id}/responder/`, { method: 'POST', body: datos }),
};
export const beneficiosApi = {
  promociones: () => solicitar('/promociones/mis-promociones/'),
  recomendaciones: () => solicitar('/recomendaciones/'),
  actualizar: () => solicitar('/recomendaciones/actualizar/', { method: 'POST', body: {} }),
};
export const estadisticasApi = (dias = 90) => solicitar(`/estadisticas/${consulta({ dias })}`);
