import { BrowserRouter, Link, Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ADMIN_URL } from './services/api';
import Layout from './components/Layout';
import { EmptyState, ErrorMessage, Loading } from './components/UI';
import { LoginPage, RegistroPage } from './pages/AuthPages';
import InicioPage from './pages/InicioPage';
import { ComplejoPage, ComplejosPage } from './pages/CatalogoPages';
import CanchaPage from './pages/CanchaPage';
import { ReservaDetallePage, ReservasPage } from './pages/ReservasPages';
import EncuestasPage from './pages/EncuestasPage';
import BeneficiosPage from './pages/BeneficiosPage';
import EstadisticasPage from './pages/EstadisticasPage';
import PerfilPage from './pages/PerfilPage';

function AccesoCliente() {
  const { usuario, cargando, error, cargarSesion, cerrarSesion } = useAuth();
  if (cargando) return <Loading />;
  if (error) return <main className="standalone"><ErrorMessage mensaje={error} /><div className="row"><button className="button primary" onClick={cargarSesion}>Volver a conectar</button><button className="button secondary" onClick={cerrarSesion}>Volver al login</button></div></main>;
  if (!usuario) return <Navigate to="/login" replace />;
  if (usuario.rol !== 'CLIENTE') return <main className="standalone"><EmptyState titulo="Esta es una cuenta administrativa" descripcion="Gestiona tus complejos desde el panel de administración."><div className="row wrap"><a className="button primary" href={ADMIN_URL}>Abrir administración</a><button className="button secondary" onClick={cerrarSesion}>Cerrar sesión</button></div></EmptyState></main>;
  return <Outlet />;
}

// Cada ruta se corresponde con una página. Las pantallas personales requieren sesión.
export default function App() {
  return <BrowserRouter><AuthProvider><Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/registro" element={<RegistroPage />} />
    <Route element={<AccesoCliente />}><Route element={<Layout />}>
      <Route index element={<InicioPage />} />
      <Route path="complejos" element={<ComplejosPage />} />
      <Route path="complejos/:id" element={<ComplejoPage />} />
      <Route path="canchas/:id" element={<CanchaPage />} />
      <Route path="reservas" element={<ReservasPage />} />
      <Route path="reservas/:id" element={<ReservaDetallePage />} />
      <Route path="encuestas" element={<EncuestasPage />} />
      <Route path="beneficios" element={<BeneficiosPage />} />
      <Route path="estadisticas" element={<EstadisticasPage />} />
      <Route path="perfil" element={<PerfilPage />} />
      <Route path="*" element={<EmptyState titulo="Esta página no existe" descripcion="Vuelve a tu espacio para continuar."><Link to="/" className="button primary">Ir a mi inicio</Link></EmptyState>} />
    </Route></Route>
  </Routes></AuthProvider></BrowserRouter>;
}
