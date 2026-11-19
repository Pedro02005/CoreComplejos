import { useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { useCarga } from '../hooks/useCarga';
import { reservasApi } from '../services/api';
import { Carga, EmptyState, ErrorMessage, EstadoBadge, PageHeader, ReservaCard, SuccessMessage } from '../components/UI';
import { dinero, estadoReserva, fechaHora, hora, puedeCancelar } from '../utils';

export function ReservasPage() {
  const [filtro, setFiltro] = useState('Todas');
  const carga = useCarga(reservasApi.listar);
  const reservas = carga.datos?.filter((reserva) => {
    const estado = estadoReserva(reserva);
    return filtro === 'Todas' || (filtro === 'Próximas' ? ['Confirmada', 'En curso'].includes(estado) : estado === filtro);
  }) || [];
  return <><PageHeader titulo="Mis reservas" descripcion="Tus próximos partidos y el historial de tus encuentros."><Link className="button primary" to="/complejos">Nueva reserva</Link></PageHeader><div className="tabs" aria-label="Filtrar reservas">{['Todas', 'Próximas', 'Finalizada', 'Cancelada'].map((valor) => <button key={valor} className={filtro === valor ? 'active' : ''} aria-pressed={filtro === valor} onClick={() => setFiltro(valor)}>{valor === 'Finalizada' ? 'Finalizadas' : valor === 'Cancelada' ? 'Canceladas' : valor}</button>)}</div><Carga estado={carga}>{reservas.length ? <section className="panel reservation-list">{reservas.map((reserva) => <ReservaCard key={reserva.id} reserva={reserva} />)}</section> : <EmptyState titulo="No hay reservas para mostrar" descripcion="Tus reservas aparecerán aquí cuando confirmes un horario." icono="calendar"><Link className="button secondary" to="/complejos">Buscar una cancha</Link></EmptyState>}</Carga></>;
}

export function ReservaDetallePage() {
  const { id } = useParams();
  const ubicacion = useLocation();
  const carga = useCarga(() => reservasApi.detalle(id), [id]);
  const [mostrarCancelacion, setMostrarCancelacion] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState(ubicacion.state?.mensaje || '');
  const [enviando, setEnviando] = useState(false);
  const reserva = carga.datos;
  async function cancelar(evento) {
    evento.preventDefault(); setError(''); setEnviando(true);
    try {
      await reservasApi.cancelar(id, motivo); setMostrarCancelacion(false);
      setMensaje('Reserva cancelada. Puedes contarnos el motivo en tu encuesta pendiente.'); carga.recargar();
    } catch (err) { setError(err.message); }
    finally { setEnviando(false); }
  }
  return <><Link className="back-link" to="/reservas">Volver a mis reservas</Link><SuccessMessage mensaje={mensaje} /><Carga estado={carga}>{reserva && <><PageHeader titulo={`Reserva #${reserva.id}`} descripcion={`${reserva.complejo} · ${reserva.cancha}`}><EstadoBadge reserva={reserva} /></PageHeader><div className="two-columns"><section className="panel"><h2>Datos de tu reserva</h2><dl className="detail-list"><div><dt>Cancha</dt><dd>{reserva.cancha}</dd></div><div><dt>Complejo</dt><dd>{reserva.complejo}</dd></div><div><dt>Inicio</dt><dd>{fechaHora(reserva.inicio)}</dd></div><div><dt>Fin</dt><dd>{fechaHora(reserva.fin)}</dd></div></dl><div className="total-row"><span>Total de la reserva</span><strong>{dinero(reserva.total)}</strong></div>{reserva.estado === 'CANCELADA' ? <Link className="button secondary" to="/encuestas">Ver mis encuestas</Link> : puedeCancelar(reserva) ? <><p className="small-text">Puedes cancelar hasta el {fechaHora(reserva.cancelable_hasta)}.</p>{!mostrarCancelacion && <button className="button danger-outline" onClick={() => { setMensaje(''); setMostrarCancelacion(true); }}>Cancelar esta reserva</button>}</> : <p className="notice info">{estadoReserva(reserva) === 'Finalizada' ? 'Este encuentro terminó. Puedes revisar tus encuestas pendientes.' : 'El plazo de cancelación de esta reserva terminó.'}</p>}<ErrorMessage mensaje={error} />{mostrarCancelacion && <form className="cancel-form form-stack" onSubmit={cancelar}><h3>¿Deseas cancelar esta reserva?</h3><p>El horario quedará disponible para otras personas.</p><label>Motivo <small>(opcional)</small><textarea maxLength={500} value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3} /></label><div className="row wrap"><button className="button danger" disabled={enviando}>{enviando ? 'Cancelando…' : 'Confirmar cancelación'}</button><button className="button secondary" type="button" disabled={enviando} onClick={() => setMostrarCancelacion(false)}>Conservar reserva</button></div></form>}</section><section className="panel"><h2>Desglose de tarifas</h2><div className="table-scroll"><table><thead><tr><th>Horario</th><th>Precio/h</th><th>Subtotal</th></tr></thead><tbody>{reserva.detalles_precio.map((tramo) => <tr key={tramo.id}><td>{hora(tramo.inicio)} – {hora(tramo.fin)}</td><td>{dinero(tramo.valor_hora)}</td><td>{dinero(tramo.subtotal)}</td></tr>)}</tbody></table></div><p className="small-text">El total final puede incluir una promoción aplicada. Consulta el historial de promociones en Mis beneficios.</p><Link to="/beneficios" className="text-link">Ver mis beneficios</Link></section></div><section className="panel"><h2>Historial de la reserva</h2><ol className="timeline">{reserva.historial.map((evento) => <li key={evento.id}><strong>{evento.evento === 'CREACION' ? 'Reserva confirmada' : 'Reserva cancelada'}</strong><span>{fechaHora(evento.fecha)} · {evento.actor}</span>{evento.motivo && <p>{evento.motivo}</p>}</li>)}</ol></section></>}</Carga></>;
}
