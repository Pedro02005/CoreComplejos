import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useCarga } from '../hooks/useCarga';
import { beneficiosApi, catalogoApi, reservasApi } from '../services/api';
import { Carga, EmptyState, ErrorMessage, Icon, Loading, PageHeader } from '../components/UI';
import { DEPORTES, DIAS, dinero, fechaHora, fechaLocal, hora } from '../utils';

export default function CanchaPage() {
  const { id } = useParams();
  const [parametros] = useSearchParams();
  const [dia, setDia] = useState(fechaLocal());
  const [duracion, setDuracion] = useState('60');
  const [promocion, setPromocion] = useState(parametros.get('promocion') || '');
  const [opciones, setOpciones] = useState(null);
  const [seleccion, setSeleccion] = useState(null);
  const [cotizacion, setCotizacion] = useState(null);
  const [error, setError] = useState('');
  const [buscando, setBuscando] = useState(false);
  const [cotizando, setCotizando] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const navegar = useNavigate();
  const carga = useCarga(async () => {
    const [cancha, promociones] = await Promise.all([catalogoApi.cancha(id), beneficiosApi.promociones()]);
    return { cancha, promociones: promociones.disponibles };
  }, [id]);
  const cancha = carga.datos?.cancha;
  const promociones = carga.datos?.promociones || [];
  useEffect(() => {
    if (carga.datos && !carga.datos.promociones.some((item) => String(item.id) === promocion)) setPromocion('');
  }, [carga.datos]);

  function limpiarSeleccion() { setSeleccion(null); setCotizacion(null); setError(''); }
  async function buscar(evento) {
    evento.preventDefault(); limpiarSeleccion(); setOpciones(null); setBuscando(true);
    try { const datos = await catalogoApi.disponibilidad(id, { fecha: dia, duracion }); setOpciones(datos.opciones); }
    catch (err) { setError(err.message); }
    finally { setBuscando(false); }
  }
  // La promoción se envía como asignación personal, no como un descuento calculado en React.
  function datosReserva(intervalo) {
    return { cancha_id: Number(id), inicio: intervalo.inicio, fin: intervalo.fin, ...(promocion ? { asignacion_id: Number(promocion) } : {}) };
  }
  async function cotizar(intervalo) {
    limpiarSeleccion(); setCotizando(true);
    try { const datos = await reservasApi.cotizar(datosReserva(intervalo)); setSeleccion(intervalo); setCotizacion(datos); }
    catch (err) { setError(err.message); }
    finally { setCotizando(false); }
  }
  async function confirmar() {
    if (!seleccion || !cotizacion || confirmando) return;
    setError(''); setConfirmando(true);
    try {
      const reserva = await reservasApi.confirmar(datosReserva(seleccion));
      navegar(`/reservas/${reserva.id}`, { replace: true, state: { mensaje: 'Tu reserva se confirmó correctamente. ¡Disfruta del partido!' } });
    } catch (err) { setError(err.message); setCotizacion(null); setSeleccion(null); }
    finally { setConfirmando(false); }
  }

  return <Carga estado={carga}>{cancha && <><Link className="back-link" to={`/complejos/${cancha.complejo}`}>Volver al complejo</Link><PageHeader titulo={cancha.nombre} descripcion={`${cancha.complejo_nombre} · ${cancha.ciudad}`}><span className="badge badge-green">{DEPORTES[cancha.deporte]} · {cancha.capacidad} personas</span></PageHeader><div className="booking-grid"><section className="panel"><div className="section-heading"><h2>Encuentra tu horario</h2><Icon name="calendar" /></div><p className="muted">Reserva entre 60 y 180 minutos, con hasta 30 días de anticipación.</p><form className="form-stack" onSubmit={buscar}><div className="form-grid"><label>Fecha<input type="date" value={dia} min={fechaLocal()} max={fechaLocal(new Date(Date.now() + 30 * 86400000))} onChange={(e) => { setDia(e.target.value); setOpciones(null); limpiarSeleccion(); }} required disabled={buscando || cotizando || confirmando} /></label><label>Duración<select value={duracion} onChange={(e) => { setDuracion(e.target.value); setOpciones(null); limpiarSeleccion(); }} disabled={buscando || cotizando || confirmando}>{[60, 90, 120, 150, 180].map((minutos) => <option value={minutos} key={minutos}>{minutos} minutos</option>)}</select></label></div><label>Promoción<select value={promocion} onChange={(e) => { setPromocion(e.target.value); limpiarSeleccion(); }} disabled={buscando || cotizando || confirmando}><option value="">Reservar sin promoción</option>{promociones.map((item) => <option key={item.id} value={item.id}>{item.nombre} · {item.tipo_descuento === 'PORCENTAJE' ? `${Number(item.valor_descuento)}%` : dinero(item.valor_descuento)}</option>)}</select><small>{promociones.length ? 'El descuento se aplicará al seleccionar un horario.' : 'Puedes consultar y actualizar tus beneficios desde el menú.'}</small></label><button className="button primary" disabled={buscando || cotizando || confirmando}>{buscando ? 'Buscando horarios…' : 'Buscar horarios disponibles'}</button></form><ErrorMessage mensaje={error} />{buscando && <Loading />}{opciones !== null && <div className="slots-section"><h3>Horarios disponibles</h3>{opciones.length ? <><p className="muted">Selecciona uno para revisar el precio final.</p><div className="slots-grid">{opciones.map((intervalo) => <button type="button" key={intervalo.inicio} className={`slot ${seleccion?.inicio === intervalo.inicio ? 'selected' : ''}`} aria-pressed={seleccion?.inicio === intervalo.inicio} onClick={() => cotizar(intervalo)} disabled={cotizando || confirmando}><strong>{hora(intervalo.inicio)} – {hora(intervalo.fin)}</strong><span>{dinero(intervalo.total)} antes de descuentos</span></button>)}</div></> : <EmptyState titulo="No hay horarios disponibles" descripcion="Prueba con otra fecha o una duración diferente." icono="calendar" />}</div>}</section><aside className="panel booking-summary"><h2>Resumen de tu reserva</h2>{cotizando ? <Loading /> : cotizacion && seleccion ? <><dl className="detail-list"><div><dt>Cancha</dt><dd>{cancha.nombre}</dd></div><div><dt>Inicio</dt><dd>{fechaHora(seleccion.inicio)}</dd></div><div><dt>Fin</dt><dd>{hora(seleccion.fin)}</dd></div><div><dt>Subtotal</dt><dd>{dinero(cotizacion.subtotal_original ?? cotizacion.total)}</dd></div>{cotizacion.promocion && <div><dt>Descuento · {cotizacion.promocion.codigo}</dt><dd className="green-text">−{dinero(cotizacion.descuento)}</dd></div>}</dl><div className="total-row"><span>Total</span><strong>{dinero(cotizacion.total)}</strong></div><p className="small-text">Cancelaciones hasta 12 horas antes del inicio. El horario y el precio se vuelven a validar al confirmar.</p><button className="button primary full" onClick={confirmar} disabled={confirmando}>{confirmando ? 'Confirmando…' : 'Confirmar reserva'}</button><details className="price-details"><summary>Ver desglose de tarifas</summary>{cotizacion.detalles.map((tramo, indice) => <p key={indice}>{hora(tramo.inicio)} – {hora(tramo.fin)}<strong>{dinero(tramo.subtotal)}</strong></p>)}</details></> : <EmptyState titulo="Elige un horario" descripcion="Aquí verás el precio y los detalles antes de confirmar." icono="calendar" />}</aside></div><div className="two-columns"><section className="panel"><h2>Horarios de atención</h2>{cancha.horarios.length ? <div className="table-scroll"><table><thead><tr><th>Día</th><th>Apertura</th><th>Cierre</th></tr></thead><tbody>{cancha.horarios.map((item) => <tr key={item.id}><td>{DIAS[item.dia_semana]}</td><td>{item.apertura.slice(0, 5)}</td><td>{item.cierre.slice(0, 5)}</td></tr>)}</tbody></table></div> : <p className="muted">Todavía no hay horarios configurados.</p>}</section><section className="panel"><h2>Tarifas por hora</h2>{cancha.tarifas.length ? <div className="table-scroll"><table><thead><tr><th>Día</th><th>Franja</th><th>Precio/h</th></tr></thead><tbody>{cancha.tarifas.map((item) => <tr key={item.id}><td>{DIAS[item.dia_semana]}</td><td>{item.inicio.slice(0, 5)} – {item.fin.slice(0, 5)}</td><td>{dinero(item.valor_hora)}</td></tr>)}</tbody></table></div> : <p className="muted">Todavía no hay tarifas configuradas.</p>}</section></div></>}</Carga>;
}
