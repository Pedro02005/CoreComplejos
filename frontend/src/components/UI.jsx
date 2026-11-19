import { Link } from 'react-router-dom';
import { dinero, estadoReserva, fecha, hora } from '../utils';

// Iconos SVG pequeños: no requieren descargar imágenes ni instalar otra biblioteca.
export function Icon({ name = 'court', size = 22 }) {
  const formas = {
    court: <><rect x="4" y="2" width="16" height="20" rx="2" /><path d="M4 12h16" /><circle cx="12" cy="12" r="4" /></>,
    home: <><path d="m3 10 9-7 9 7v11h-6v-7H9v7H3Z" /></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M7 2v6M17 2v6M3 11h18m-13 5h3m3 0h3" /></>,
    survey: <><rect x="5" y="3" width="14" height="19" rx="2" /><path d="M9 2h6v4H9Zm-1 9h8m-8 4h8m-8 4h5" /></>,
    gift: <><rect x="3" y="8" width="18" height="4" rx="1" /><path d="M5 12v9h14v-9M12 8v13m0-13C4 8 6 0 10 4l2 4c8 0 6-8 2-4Z" /></>,
    chart: <><path d="M4 3v18h17M8 17v-5m5 5V6m5 11V9" /></>,
    user: <><circle cx="12" cy="7" r="4" /><path d="M4 22v-3a8 8 0 0 1 16 0v3" /></>,
    logout: <><path d="M10 4H4v16h6m4-13 5 5-5 5m-6-5h11" /></>,
    pin: <><path d="M19 9c0 6-7 12-7 12S5 15 5 9a7 7 0 1 1 14 0Z" /><circle cx="12" cy="9" r="2" /></>,
    check: <path d="m5 12 4 4L20 5" />,
    menu: <path d="M3 6h18M3 12h18M3 18h18" />,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{formas[name] || formas.court}</svg>;
}
export function Brand() { return <div className="brand"><span className="brand-mark"><Icon name="court" size={25} /></span><span>Reservas<span className="brand-sub">deportivas</span></span></div>; }
export function PageHeader({ titulo, descripcion, children }) { return <header className="page-header"><div><h1>{titulo}</h1>{descripcion && <p>{descripcion}</p>}</div>{children}</header>; }
export function ErrorMessage({ mensaje }) { return mensaje ? <div className="notice error" role="alert">{mensaje}</div> : null; }
export function SuccessMessage({ mensaje }) { return mensaje ? <div className="notice success" role="status"><Icon name="check" size={18} />{mensaje}</div> : null; }
export function Loading() { return <div className="loading" role="status"><span className="spinner" />Cargando información…</div>; }
export function EmptyState({ titulo, descripcion, children, icono = 'court' }) { return <div className="empty-state"><span className="empty-icon"><Icon name={icono} size={30} /></span><h3>{titulo}</h3><p>{descripcion}</p>{children}</div>; }
export function Carga({ estado, children }) {
  if (estado.cargando) return <Loading />;
  if (estado.error) return <div><ErrorMessage mensaje={estado.error} /><button className="button secondary" onClick={estado.recargar}>Volver a intentar</button></div>;
  return children;
}
export function StatCard({ titulo, valor, detalle, icono = 'chart' }) { return <article className="stat-card"><div><span className="stat-label">{titulo}</span><strong>{valor ?? '—'}</strong>{detalle && <small>{detalle}</small>}</div><span className="stat-icon"><Icon name={icono} /></span></article>; }
export function EstadoBadge({ reserva }) {
  const estado = estadoReserva(reserva);
  return <span className={`badge ${estado === 'Cancelada' ? 'badge-red' : estado === 'Finalizada' ? 'badge-gray' : 'badge-green'}`}>{estado}</span>;
}
export function ReservaCard({ reserva }) { return <article className="reservation-card"><div className="reservation-icon"><Icon name="calendar" /></div><div className="reservation-main"><div className="row wrap"><h3>{reserva.cancha}</h3><EstadoBadge reserva={reserva} /></div><p>{reserva.complejo}</p><span>{fecha(reserva.inicio)} · {hora(reserva.inicio)} – {hora(reserva.fin)}</span></div><div className="reservation-end"><strong>{dinero(reserva.total)}</strong><Link className="text-link" to={`/reservas/${reserva.id}`}>Ver detalle</Link></div></article>; }
export function Opciones({ opciones }) { return Object.entries(opciones).map(([valor, etiqueta]) => <option key={valor} value={valor}>{etiqueta}</option>); }
export function Paginacion({ datos, pagina, cambiar }) { return datos?.count > 20 ? <div className="pagination"><button className="button secondary" disabled={!datos.previous} onClick={() => cambiar(pagina - 1)}>Anterior</button><span>Página {pagina} · {datos.count} resultados</span><button className="button secondary" disabled={!datos.next} onClick={() => cambiar(pagina + 1)}>Siguiente</button></div> : null; }
