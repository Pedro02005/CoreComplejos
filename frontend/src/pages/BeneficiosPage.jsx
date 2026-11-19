import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCarga } from '../hooks/useCarga';
import { beneficiosApi } from '../services/api';
import {
  Carga,
  EmptyState,
  ErrorMessage,
  Icon,
  PageHeader,
  SuccessMessage,
} from '../components/UI';
import { dinero, fechaHora } from '../utils';

export default function BeneficiosPage() {
  // Consultar beneficios es una lectura. El botón Actualizar ejecuta las reglas del backend.
  const [pestana, setPestana] = useState('disponibles');
  const [actualizando, setActualizando] = useState(false);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');
  const carga = useCarga(async () => {
    const [promociones, recomendaciones] = await Promise.all([
      beneficiosApi.promociones(),
      beneficiosApi.recomendaciones(),
    ]);
    return { ...promociones, recomendaciones: recomendaciones.recomendaciones };
  });
  async function actualizar() {
    setActualizando(true);
    setError('');
    setMensaje('');
    try {
      const resultado = await beneficiosApi.actualizar();
      setMensaje(
        resultado.promociones_nuevas
          ? `Beneficios actualizados. Tienes ${resultado.promociones_nuevas} nuevas promociones.`
          : 'Beneficios actualizados. Ya puedes revisar tus recomendaciones y promociones vigentes.'
      );
      carga.recargar();
    } catch (err) {
      setError(err.message);
    } finally {
      setActualizando(false);
    }
  }
  const lista = carga.datos?.[pestana] || [];
  return (
    <>
      <PageHeader
        titulo="Beneficios para seguir jugando"
        descripcion="Promociones y recomendaciones basadas en tu actividad y tus opiniones."
      >
        <button
          className="button primary"
          onClick={actualizar}
          disabled={actualizando || carga.cargando}
        >
          {actualizando ? 'Actualizando…' : 'Actualizar beneficios'}
        </button>
      </PageHeader>
      <ErrorMessage mensaje={error} />
      <SuccessMessage mensaje={mensaje} />
      <div className="tabs" aria-label="Tipos de beneficios">
        {[
          ['disponibles', 'Promociones disponibles'],
          ['utilizadas', 'Promociones utilizadas'],
          ['recomendaciones', 'Recomendaciones'],
        ].map(([valor, titulo]) => (
          <button
            key={valor}
            className={pestana === valor ? 'active' : ''}
            aria-pressed={pestana === valor}
            onClick={() => setPestana(valor)}
          >
            {titulo}
            {carga.datos ? ` (${carga.datos[valor].length})` : ''}
          </button>
        ))}
      </div>
      <Carga estado={carga}>
        {lista.length ? (
          <div className="cards-grid">
            {lista.map((item) =>
              pestana === 'recomendaciones' ? (
                <article className="panel benefit-card" key={item.id}>
                  <span className="stat-icon">
                    <Icon name="chart" />
                  </span>
                  <h2>{item.titulo}</h2>
                  <p>{item.motivo}</p>
                  <p className="small-text">Vigente hasta {fechaHora(item.vence_en)}</p>
                  {['EVALUAR_DESCUENTO', 'EVALUAR_BENEFICIO_FIDELIDAD'].includes(
                    item.accion_sugerida
                  ) ? (
                    <button
                      className="button secondary full"
                      onClick={() => setPestana('disponibles')}
                    >
                      Ver mis promociones
                    </button>
                  ) : (
                    <Link className="button secondary full" to="/complejos">
                      Explorar canchas
                    </Link>
                  )}
                </article>
              ) : (
                <article className="panel benefit-card" key={item.id}>
                  <div className="row between">
                    <span className="stat-icon">
                      <Icon name="gift" />
                    </span>
                    <span
                      className={`badge ${pestana === 'utilizadas' ? 'badge-gray' : 'badge-green'}`}
                    >
                      {pestana === 'utilizadas' ? 'Utilizada' : 'Disponible'}
                    </span>
                  </div>
                  <strong className="discount-value">
                    {item.tipo_descuento === 'PORCENTAJE'
                      ? `${Number(item.valor_descuento)}%`
                      : dinero(item.valor_descuento)}
                    <span> de descuento</span>
                  </strong>
                  <h2>{item.nombre}</h2>
                  <p>{item.descripcion || item.motivo_asignacion}</p>
                  <div className="promo-code">{item.codigo}</div>
                  {pestana === 'disponibles' ? (
                    <>
                      <p className="small-text">Válida hasta {fechaHora(item.vence_en)}</p>
                      <Link className="button primary full" to={`/complejos?promocion=${item.id}`}>
                        Usar al reservar
                      </Link>
                    </>
                  ) : (
                    <>
                      <p className="small-text">
                        Usada el {fechaHora(item.fecha_uso)} · Ahorro:{' '}
                        {dinero(item.descuento_aplicado)}
                      </p>
                      <Link className="text-link" to={`/reservas/${item.reserva_utilizada}`}>
                        Ver reserva #{item.reserva_utilizada}
                      </Link>
                    </>
                  )}
                </article>
              )
            )}
          </div>
        ) : (
          <EmptyState
            titulo={
              pestana === 'recomendaciones'
                ? 'Tus recomendaciones están por llegar'
                : pestana === 'utilizadas'
                  ? 'Aún no has utilizado promociones'
                  : 'No tienes promociones disponibles'
            }
            descripcion={
              pestana === 'recomendaciones'
                ? 'Responde tus encuestas y actualiza los beneficios para conocer tus sugerencias personales.'
                : pestana === 'utilizadas'
                  ? 'Cuando reserves con una promoción, podrás consultar aquí su historial.'
                  : 'Actualiza tus beneficios. Las promociones dependen de tu actividad y de las campañas vigentes.'
            }
            icono="gift"
          />
        )}
      </Carga>
    </>
  );
}
