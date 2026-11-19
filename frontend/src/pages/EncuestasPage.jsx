import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCarga } from '../hooks/useCarga';
import { encuestasApi } from '../services/api';
import { ASPECTOS, MOTIVOS, SOLUCIONES, fechaHora } from '../utils';
import {
  Carga,
  EmptyState,
  ErrorMessage,
  Opciones,
  PageHeader,
  SuccessMessage,
} from '../components/UI';

function EncuestaFormulario({ encuesta, alResponder }) {
  const cancelacion = encuesta.tipo === 'CANCELACION';
  const [datos, setDatos] = useState({
    motivo_cancelacion: '',
    hubiera_evitado: '',
    calificacion: '',
    volveria_reservar: '',
    aspecto_mejorar: '',
    comentario: '',
  });
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);
  const campo = (nombre) => ({
    value: datos[nombre],
    onChange: (e) => setDatos({ ...datos, [nombre]: e.target.value }),
  });
  async function responder(evento) {
    evento.preventDefault();
    setError('');
    setEnviando(true);
    // Cada tipo de encuesta envía solamente sus propias preguntas.
    const respuestas = cancelacion
      ? { motivo_cancelacion: datos.motivo_cancelacion, hubiera_evitado: datos.hubiera_evitado }
      : {
          calificacion: Number(datos.calificacion),
          volveria_reservar: datos.volveria_reservar === 'SI',
          aspecto_mejorar: datos.aspecto_mejorar,
        };
    try {
      await encuestasApi.responder(encuesta.id, { ...respuestas, comentario: datos.comentario });
      alResponder();
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }
  return (
    <article className="panel survey-card">
      <span className={`badge ${cancelacion ? 'badge-gray' : 'badge-green'}`}>
        {cancelacion ? 'Sobre tu cancelación' : 'Sobre tu experiencia'}
      </span>
      <h2>{encuesta.cancha}</h2>
      <p className="muted">
        {encuesta.complejo} · {fechaHora(encuesta.inicio)}
      </p>
      <ErrorMessage mensaje={error} />
      <form onSubmit={responder} className="form-stack">
        <fieldset disabled={enviando} className="form-stack">
          {cancelacion ? (
            <>
              <label>
                ¿Por qué cancelaste?
                <select {...campo('motivo_cancelacion')} required>
                  <option value="">Selecciona un motivo</option>
                  <Opciones opciones={MOTIVOS} />
                </select>
              </label>
              <label>
                ¿Qué habría evitado la cancelación?
                <select {...campo('hubiera_evitado')} required>
                  <option value="">Selecciona una opción</option>
                  <Opciones opciones={SOLUCIONES} />
                </select>
              </label>
            </>
          ) : (
            <>
              <label>
                ¿Cómo calificarías tu experiencia?
                <select {...campo('calificacion')} required>
                  <option value="">Selecciona una calificación</option>
                  {[1, 2, 3, 4, 5].map((numero) => (
                    <option key={numero} value={numero}>
                      {numero} de 5
                    </option>
                  ))}
                </select>
              </label>
              <label>
                ¿Volverías a reservar?
                <select {...campo('volveria_reservar')} required>
                  <option value="">Selecciona una respuesta</option>
                  <option value="SI">Sí</option>
                  <option value="NO">No</option>
                </select>
              </label>
              <label>
                ¿Qué aspecto mejorarías?
                <select {...campo('aspecto_mejorar')} required>
                  <option value="">Selecciona un aspecto</option>
                  <Opciones opciones={ASPECTOS} />
                </select>
              </label>
            </>
          )}
          <label>
            Comentario <small>(opcional)</small>
            <textarea
              {...campo('comentario')}
              rows={3}
              maxLength={1000}
              placeholder="Cuéntanos un poco más"
            />
          </label>
          <button className="button primary" disabled={enviando}>
            {enviando ? 'Enviando…' : 'Enviar encuesta'}
          </button>
        </fieldset>
      </form>
    </article>
  );
}

export default function EncuestasPage() {
  const carga = useCarga(encuestasApi.pendientes);
  const [mensaje, setMensaje] = useState('');
  function alResponder() {
    setMensaje('Gracias por tu opinión. Ahora puedes actualizar tus beneficios personales.');
    carga.recargar();
  }
  return (
    <>
      <PageHeader
        titulo="Tu opinión cuenta"
        descripcion="Ayúdanos a conocer tu experiencia y encontrar mejores opciones para ti."
      />
      <SuccessMessage mensaje={mensaje} />
      {mensaje && (
        <p>
          <Link to="/beneficios" className="text-link">
            Consultar y actualizar mis beneficios
          </Link>
        </p>
      )}
      <Carga estado={carga}>
        {carga.datos?.length ? (
          <div className="two-columns">
            {carga.datos.map((encuesta) => (
              <EncuestaFormulario key={encuesta.id} encuesta={encuesta} alResponder={alResponder} />
            ))}
          </div>
        ) : (
          <EmptyState
            titulo="Estás al día con tus encuestas"
            descripcion="Después de terminar un encuentro o cancelar una reserva, encontrarás aquí las preguntas pendientes."
            icono="survey"
          />
        )}
      </Carga>
    </>
  );
}
