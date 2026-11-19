import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useCarga } from '../hooks/useCarga';
import { catalogoApi } from '../services/api';
import { Carga, EmptyState, Icon, Opciones, PageHeader, Paginacion } from '../components/UI';
import { DEPORTES } from '../utils';

export function ComplejosPage() {
  // Se separa lo escrito del filtro aplicado para buscar únicamente al enviar el formulario.
  const [campos, setCampos] = useState({ nombre: '', ciudad: '' });
  const [filtros, setFiltros] = useState({ nombre: '', ciudad: '' });
  const [pagina, setPagina] = useState(1);
  const [parametros] = useSearchParams();
  const promocion = parametros.get('promocion');
  const sufijo = promocion ? `?promocion=${encodeURIComponent(promocion)}` : '';
  const carga = useCarga(
    () => catalogoApi.complejos({ ...filtros, page: pagina }),
    [filtros, pagina]
  );
  function buscar(evento) {
    evento.preventDefault();
    setPagina(1);
    setFiltros({ ...campos });
  }

  return (
    <>
      <PageHeader
        titulo="Encuentra tu próximo lugar"
        descripcion="Explora nuestros complejos y elige dónde quieres jugar."
      />
      {promocion && (
        <div className="notice info">
          Llevas una promoción seleccionada. Podrás revisarla antes de confirmar tu reserva.
        </div>
      )}
      <form className="filters panel" onSubmit={buscar}>
        <label>
          Nombre del complejo
          <input
            value={campos.nombre}
            onChange={(e) => setCampos({ ...campos, nombre: e.target.value })}
            placeholder="Buscar por nombre"
            maxLength={100}
          />
        </label>
        <label>
          Ciudad
          <input
            value={campos.ciudad}
            onChange={(e) => setCampos({ ...campos, ciudad: e.target.value })}
            placeholder="Por ejemplo, Quito"
            maxLength={100}
          />
        </label>
        <button className="button primary">Buscar complejos</button>
        <button
          type="button"
          className="button ghost"
          onClick={() => {
            setCampos({ nombre: '', ciudad: '' });
            setFiltros({ nombre: '', ciudad: '' });
            setPagina(1);
          }}
        >
          Limpiar
        </button>
      </form>
      <Carga estado={carga}>
        {carga.datos && (
          <>
            <p className="results-count">
              {carga.datos.count} {carga.datos.count === 1 ? 'complejo encontrado' : 'complejos encontrados'}
            </p>
            {carga.datos.results.length ? (
              <div className="cards-grid">
                {carga.datos.results.map((complejo) => (
                  <article className="catalog-card" key={complejo.id}>
                    <div className="catalog-art" aria-hidden="true">
                      <Icon name="court" size={64} />
                    </div>
                    <div className="catalog-body">
                      <span className="location">
                        <Icon name="pin" size={16} />
                        {complejo.ciudad}
                      </span>
                      <h2>{complejo.nombre}</h2>
                      <p>
                        {complejo.descripcion ||
                          'Encuentra una cancha y organiza tu próximo encuentro.'}
                      </p>
                      <p className="address">{complejo.direccion}</p>
                      <Link
                        className="button secondary full"
                        to={`/complejos/${complejo.id}${sufijo}`}
                      >
                        Ver canchas
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                titulo="No encontramos complejos"
                descripcion="Prueba con otra ciudad o cambia el nombre de búsqueda."
              />
            )}
            <Paginacion datos={carga.datos} pagina={pagina} cambiar={setPagina} />
          </>
        )}
      </Carga>
    </>
  );
}

export function ComplejoPage() {
  // La ficha ya trae sus canchas; el selector de deporte filtra esa lista.
  const { id } = useParams();
  const [deporte, setDeporte] = useState('');
  const [parametros] = useSearchParams();
  const promocion = parametros.get('promocion');
  const sufijo = promocion ? `?promocion=${encodeURIComponent(promocion)}` : '';
  const carga = useCarga(() => catalogoApi.complejo(id), [id]);
  const complejo = carga.datos;
  const canchas =
    complejo?.canchas.filter((cancha) => !deporte || cancha.deporte === deporte) || [];
  return (
    <>
      <Link className="back-link" to={`/complejos${sufijo}`}>
        Volver a los complejos
      </Link>
      <Carga estado={carga}>
        {complejo && (
          <>
            <PageHeader
              titulo={complejo.nombre}
              descripcion={`${complejo.ciudad} · ${complejo.direccion}`}
            />
            <div className="panel intro-panel">
              <span className="stat-icon">
                <Icon name="pin" />
              </span>
              <p>
                {complejo.descripcion ||
                  'Elige una cancha y consulta sus próximos horarios disponibles.'}
              </p>
            </div>
            <div className="section-heading">
              <h2>Canchas del complejo</h2>
              <label className="inline-label">
                Deporte
                <select value={deporte} onChange={(e) => setDeporte(e.target.value)}>
                  <option value="">Todos los deportes</option>
                  <Opciones opciones={DEPORTES} />
                </select>
              </label>
            </div>
            {canchas.length ? (
              <div className="cards-grid">
                {canchas.map((cancha) => (
                  <article className="panel court-card" key={cancha.id}>
                    <div className="row between">
                      <span className="stat-icon">
                        <Icon name="court" />
                      </span>
                      <span className="badge badge-green">{DEPORTES[cancha.deporte]}</span>
                    </div>
                    <h2>{cancha.nombre}</h2>
                    <p>Capacidad para {cancha.capacidad} personas</p>
                    <Link className="button primary full" to={`/canchas/${cancha.id}${sufijo}`}>
                      Consultar disponibilidad
                    </Link>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                titulo="No hay canchas para mostrar"
                descripcion="Elige otro deporte o vuelve más adelante."
              />
            )}
          </>
        )}
      </Carga>
    </>
  );
}
