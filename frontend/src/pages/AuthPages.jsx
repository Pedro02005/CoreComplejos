import { useState } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.js';
import { ADMIN_URL, cuentasApi } from '../services/api';
import { Brand, ErrorMessage, Icon, Loading, SuccessMessage } from '../components/UI';

function AuthLayout({ children, registro = false }) {
  return (
    <main className="auth-layout">
      <section className="auth-story">
        <Brand />
        <div className="auth-story-content">
          <span className="eyebrow light">MÁS DEPORTE, MÁS MOMENTOS</span>
          <h1>
            Tu cancha.
            <br />
            Tu horario.
            <br />
            <span>Tu próximo partido.</span>
          </h1>
          <p>
            Encuentra tu espacio, reserva con facilidad y disfruta de los beneficios de seguir
            jugando.
          </p>
          <div className="court-illustration" aria-hidden="true">
            <div className="court-lines">
              <span />
              <i />
            </div>
          </div>
          <div className="auth-features">
            <span>
              <Icon name="check" size={18} />
              Reserva en pocos pasos
            </span>
            <span>
              <Icon name="check" size={18} />
              Beneficios para ti
            </span>
          </div>
        </div>
        <small>Reservas deportivas · Ecuador</small>
      </section>
      <section className="auth-form-side">
        <div className="auth-mobile-brand">
          <Brand />
        </div>
        <div className={`auth-form-card ${registro ? 'registration-card' : ''}`}>{children}</div>
        <p className="auth-admin">
          ¿Administras un complejo? <a href={ADMIN_URL}>Acceso administrativo</a>
        </p>
      </section>
    </main>
  );
}

export function LoginPage() {
  // Iniciar sesión obtiene los tokens y después consulta el perfil de la cuenta.
  const { usuario, cargando, iniciarSesion } = useAuth();
  const [datos, setDatos] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [parametros] = useSearchParams();
  const navegar = useNavigate();
  if (cargando) return <Loading />;
  if (usuario) return <Navigate to="/" replace />;
  async function entrar(evento) {
    evento.preventDefault();
    setError('');
    setEnviando(true);
    try {
      await iniciarSesion(datos);
      navegar('/', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }
  return (
    <AuthLayout>
      <span className="eyebrow">BIENVENIDO A TU ESPACIO</span>
      <h2>Inicia sesión</h2>
      <p className="auth-intro">Todo listo para volver a jugar.</p>
      <SuccessMessage
        mensaje={
          parametros.has('registro') ? 'Tu cuenta está lista. Inicia sesión para comenzar.' : ''
        }
      />
      <ErrorMessage mensaje={error} />
      <form onSubmit={entrar} className="form-stack">
        <label>
          Usuario
          <input
            name="username"
            autoComplete="username"
            value={datos.username}
            onChange={(e) => setDatos({ ...datos, username: e.target.value })}
            required
            placeholder="Tu nombre de usuario"
          />
        </label>
        <label>
          Contraseña
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            value={datos.password}
            onChange={(e) => setDatos({ ...datos, password: e.target.value })}
            required
            placeholder="Tu contraseña"
          />
        </label>
        <button className="button primary full" disabled={enviando}>
          {enviando ? 'Ingresando…' : 'Iniciar sesión'}
        </button>
      </form>
      <p className="auth-switch">
        ¿Primera vez aquí? <Link to="/registro">Crea tu cuenta</Link>
      </p>
    </AuthLayout>
  );
}

export function RegistroPage() {
  // El registro solo envía datos personales; el servidor asigna siempre el rol de cliente.
  const { usuario } = useAuth();
  const [datos, setDatos] = useState({
    first_name: '',
    last_name: '',
    username: '',
    email: '',
    cedula: '',
    telefono: '',
    password: '',
    password_confirmacion: '',
  });
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);
  const navegar = useNavigate();
  if (usuario) return <Navigate to="/" replace />;
  const campo = (nombre) => ({
    name: nombre,
    value: datos[nombre],
    onChange: (e) => setDatos({ ...datos, [nombre]: e.target.value }),
  });
  async function registrar(evento) {
    evento.preventDefault();
    setError('');
    if (datos.password !== datos.password_confirmacion) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    setEnviando(true);
    try {
      await cuentasApi.registro(datos);
      navegar('/login?registro=1', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }
  return (
    <AuthLayout registro>
      <span className="eyebrow">EMPIEZA A JUGAR</span>
      <h2>Crea tu cuenta</h2>
      <p className="auth-intro">Tus reservas y beneficios, en un solo lugar.</p>
      <ErrorMessage mensaje={error} />
      <form onSubmit={registrar} className="form-stack">
        <div className="form-grid">
          <label>
            Nombres
            <input {...campo('first_name')} autoComplete="given-name" maxLength={150} required />
          </label>
          <label>
            Apellidos
            <input {...campo('last_name')} autoComplete="family-name" maxLength={150} required />
          </label>
        </div>
        <label>
          Usuario
          <input {...campo('username')} autoComplete="username" maxLength={150} required />
        </label>
        <label>
          Correo electrónico
          <input {...campo('email')} type="email" autoComplete="email" maxLength={254} required />
        </label>
        <div className="form-grid">
          <label>
            Cédula <small>(opcional)</small>
            <input {...campo('cedula')} inputMode="numeric" pattern="[0-9]{10}" maxLength={10} />
          </label>
          <label>
            Celular <small>(opcional)</small>
            <input
              {...campo('telefono')}
              type="tel"
              autoComplete="tel"
              pattern="09[0-9]{8}"
              maxLength={10}
              placeholder="09XXXXXXXX"
            />
          </label>
        </div>
        <label>
          Contraseña
          <input
            {...campo('password')}
            type="password"
            autoComplete="new-password"
            minLength={8}
            required
          />
          <small>Al menos 8 caracteres. Combina letras y números; evita datos personales.</small>
        </label>
        <label>
          Confirmar contraseña
          <input
            {...campo('password_confirmacion')}
            type="password"
            autoComplete="new-password"
            minLength={8}
            required
          />
        </label>
        <button className="button primary full" disabled={enviando}>
          {enviando ? 'Creando cuenta…' : 'Crear cuenta'}
        </button>
      </form>
      <p className="auth-switch">
        ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
      </p>
    </AuthLayout>
  );
}
