import { useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.js';
import { Brand, Icon } from './UI';

const enlaces = [
  ['/', 'Mi inicio', 'home'],
  ['/complejos', 'Reservar cancha', 'court'],
  ['/reservas', 'Mis reservas', 'calendar'],
  ['/encuestas', 'Encuestas', 'survey'],
  ['/beneficios', 'Mis beneficios', 'gift'],
  ['/estadisticas', 'Mis estadísticas', 'chart'],
  ['/perfil', 'Mi perfil', 'user'],
];

export default function Layout() {
  // Esta estructura se comparte entre todas las páginas privadas mediante Outlet.
  const { usuario, cerrarSesion } = useAuth();
  const [menuAbierto, setMenuAbierto] = useState(false);
  const ubicacion = useLocation();
  const nombreSeccion = ubicacion.pathname.startsWith('/canchas/')
    ? 'Reservar cancha'
    : enlaces.find(([ruta]) =>
        ruta === '/' ? ubicacion.pathname === '/' : ubicacion.pathname.startsWith(ruta)
      )?.[1] || 'Mi espacio';

  return (
    <div className="app-shell">
      <a className="skip-link" href="#contenido">
        Ir al contenido
      </a>
      <aside className={`sidebar ${menuAbierto ? 'is-open' : ''}`}>
        <Link className="brand-link" to="/" onClick={() => setMenuAbierto(false)}>
          <Brand />
        </Link>
        <p className="nav-label">MI ESPACIO</p>
        <nav aria-label="Menú principal">
          {enlaces.map(([ruta, texto, icono]) => (
            <NavLink key={ruta} to={ruta} end={ruta === '/'} onClick={() => setMenuAbierto(false)}>
              <Icon name={icono} />
              {texto}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <p>
            Tu próximo partido
            <br />
            <strong>empieza aquí.</strong>
          </p>
          <button className="logout-button" onClick={cerrarSesion}>
            <Icon name="logout" size={20} />
            Cerrar sesión
          </button>
        </div>
      </aside>
      {menuAbierto && (
        <button
          className="menu-backdrop"
          aria-label="Cerrar menú"
          onClick={() => setMenuAbierto(false)}
        />
      )}
      <div className="workspace">
        <header className="topbar">
          <div className="row">
            <button
              className="icon-button mobile-menu"
              aria-label="Abrir menú"
              aria-expanded={menuAbierto}
              onClick={() => setMenuAbierto(!menuAbierto)}
            >
              <Icon name="menu" />
            </button>
            <span>{nombreSeccion}</span>
          </div>
          <Link to="/perfil" className="user-chip">
            <span className="avatar">
              {(usuario.first_name || usuario.username).charAt(0).toUpperCase()}
            </span>
            <span>
              {usuario.first_name || usuario.username}
              <small>Cliente</small>
            </span>
          </Link>
        </header>
        <main id="contenido" className="main-content">
          <Outlet />
        </main>
        <footer className="app-footer">
          Reservas deportivas · Horarios de Ecuador · Precios en USD
        </footer>
      </div>
    </div>
  );
}
