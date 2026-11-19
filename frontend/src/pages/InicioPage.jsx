import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.js';
import { useCarga } from '../hooks/useCarga';
import { beneficiosApi, encuestasApi, reservasApi } from '../services/api';
import { Carga, EmptyState, Icon, PageHeader, ReservaCard, StatCard } from '../components/UI';

export default function InicioPage() {
  // El inicio resume los datos reales del cliente y ofrece accesos a las demás pantallas.
  const { usuario } = useAuth();
  // Las consultas son independientes y se hacen juntas para cargar el resumen.
  const carga = useCarga(async () => {
    const [reservas, encuestas, promociones, recomendaciones] = await Promise.all([
      reservasApi.listar(),
      encuestasApi.pendientes(),
      beneficiosApi.promociones(),
      beneficiosApi.recomendaciones(),
    ]);
    return { reservas, encuestas, promociones, recomendaciones };
  });
  const datos = carga.datos;
  const proximas =
    datos?.reservas
      .filter((reserva) => reserva.estado === 'CONFIRMADA' && new Date(reserva.fin) > new Date())
      .sort((a, b) => new Date(a.inicio) - new Date(b.inicio)) || [];

  return (
    <>
      <PageHeader
        titulo={`Hola, ${usuario.first_name || usuario.username}`}
        descripcion="Tus reservas y beneficios, listos para tu próximo partido."
      />
      <section className="welcome-banner">
        <div>
          <span className="eyebrow light">TU TIEMPO PARA JUGAR</span>
          <h2>Haz espacio para el deporte.</h2>
          <p>Elige tu cancha y encuentra el horario que va contigo.</p>
          <Link className="button white" to="/complejos">
            Reservar una cancha
          </Link>
        </div>
        <div className="welcome-court" aria-hidden="true">
          <Icon name="court" size={130} />
        </div>
      </section>
      <Carga estado={carga}>
        {datos && (
          <>
            <div className="stats-grid">
              <StatCard titulo="Próximas reservas" valor={proximas.length} icono="calendar" />
              <StatCard
                titulo="Encuestas pendientes"
                valor={datos.encuestas.length}
                icono="survey"
              />
              <StatCard
                titulo="Promociones disponibles"
                valor={datos.promociones.cantidad_disponibles}
                icono="gift"
              />
              <StatCard
                titulo="Recomendaciones"
                valor={datos.recomendaciones.cantidad}
                icono="chart"
              />
            </div>
            <div className="dashboard-grid">
              <section className="panel">
                <div className="section-heading">
                  <h2>Tus próximas reservas</h2>
                  <Link className="text-link" to="/reservas">
                    Ver todas
                  </Link>
                </div>
                {proximas.length ? (
                  proximas
                    .slice(0, 3)
                    .map((reserva) => <ReservaCard key={reserva.id} reserva={reserva} />)
                ) : (
                  <EmptyState
                    titulo="Tu próximo partido está por llegar"
                    descripcion="Explora los complejos y encuentra un espacio para jugar."
                  >
                    <Link className="button secondary" to="/complejos">
                      Explorar complejos
                    </Link>
                  </EmptyState>
                )}
              </section>
              <section className="panel">
                <div className="section-heading">
                  <h2>También para ti</h2>
                </div>
                <Link className="quick-link" to="/encuestas">
                  <span className="stat-icon">
                    <Icon name="survey" />
                  </span>
                  <div>
                    <h3>Tu opinión cuenta</h3>
                    <p>
                      {datos.encuestas.length
                        ? `Tienes ${datos.encuestas.length} encuestas por responder.`
                        : 'Tus encuestas aparecerán después de jugar o cancelar.'}
                    </p>
                  </div>
                </Link>
                <Link className="quick-link" to="/beneficios">
                  <span className="stat-icon">
                    <Icon name="gift" />
                  </span>
                  <div>
                    <h3>Beneficios personales</h3>
                    <p>Descubre tus promociones y recomendaciones.</p>
                  </div>
                </Link>
                <Link className="quick-link" to="/estadisticas">
                  <span className="stat-icon">
                    <Icon name="chart" />
                  </span>
                  <div>
                    <h3>Tu actividad deportiva</h3>
                    <p>Consulta tus preferencias y estadísticas.</p>
                  </div>
                </Link>
              </section>
            </div>
          </>
        )}
      </Carga>
    </>
  );
}
