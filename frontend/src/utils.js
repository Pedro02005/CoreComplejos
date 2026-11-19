// Fechas y horas de la interfaz siempre corresponden a Ecuador continental.
const ZONA = 'America/Guayaquil';
export const dinero = (valor) =>
  new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' }).format(Number(valor || 0));
export const fechaHora = (valor) =>
  new Intl.DateTimeFormat('es-EC', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: ZONA,
  }).format(new Date(valor));
export const fecha = (valor) =>
  new Intl.DateTimeFormat('es-EC', { dateStyle: 'medium', timeZone: ZONA }).format(new Date(valor));
export const hora = (valor) =>
  new Intl.DateTimeFormat('es-EC', { hour: '2-digit', minute: '2-digit', timeZone: ZONA }).format(
    new Date(valor)
  );
export function fechaLocal(valor = new Date()) {
  const partes = new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone: ZONA,
  }).formatToParts(valor);
  const obtener = (tipo) => partes.find((parte) => parte.type === tipo).value;
  return `${obtener('year')}-${obtener('month')}-${obtener('day')}`;
}
export function estadoReserva(reserva, ahora = Date.now()) {
  if (reserva.estado === 'CANCELADA') return 'Cancelada';
  if (new Date(reserva.fin).getTime() <= ahora) return 'Finalizada';
  if (new Date(reserva.inicio).getTime() <= ahora) return 'En curso';
  return 'Confirmada';
}
export function puedeCancelar(reserva, ahora = Date.now()) {
  return reserva.estado === 'CONFIRMADA' && ahora <= new Date(reserva.cancelable_hasta).getTime();
}
export const DEPORTES = {
  FUTBOL: 'Fútbol',
  BASQUET: 'Básquet',
  VOLEY: 'Vóley',
  TENIS: 'Tenis',
  PADEL: 'Pádel',
};
export const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
export const FRANJAS = { MANANA: 'Mañana', TARDE: 'Tarde', NOCHE: 'Noche' };
export const MOTIVOS = {
  PRECIO: 'Precio elevado',
  HORARIO: 'Problemas de horario',
  UBICACION: 'Ubicación',
  CAMBIO_PLANES: 'Cambio de planes',
  INSTALACIONES: 'Instalaciones',
  OTRO: 'Otro motivo',
};
export const SOLUCIONES = {
  DESCUENTO: 'Un descuento',
  CAMBIO_HORARIO: 'Otro horario',
  OTRA_CANCHA: 'Otra cancha o complejo',
  MEJORES_INSTALACIONES: 'Mejores instalaciones',
  NADA: 'Nada hubiera evitado cancelar',
  OTRO: 'Otra solución',
};
export const ASPECTOS = {
  PRECIO: 'Precio',
  INSTALACIONES: 'Instalaciones',
  ATENCION: 'Atención al cliente',
  DISPONIBILIDAD: 'Horarios disponibles',
  NINGUNO: 'Ninguno',
  OTRO: 'Otro aspecto',
};
