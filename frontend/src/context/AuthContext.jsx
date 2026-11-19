import { createContext, useContext, useEffect, useState } from 'react';
import { borrarTokens, cuentasApi, guardarTokens, obtenerTokens } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  function cerrarSesion() { borrarTokens(); setUsuario(null); setError(''); }

  async function cargarSesion() {
    setCargando(true); setError('');
    if (!obtenerTokens()?.access) { setCargando(false); return; }
    try { setUsuario(await cuentasApi.perfil()); }
    catch (err) { if (obtenerTokens()) setError(err.message); }
    finally { setCargando(false); }
  }

  useEffect(() => {
    cargarSesion();
    window.addEventListener('sesion-vencida', cerrarSesion);
    return () => window.removeEventListener('sesion-vencida', cerrarSesion);
  }, []);

  async function iniciarSesion(datos) {
    guardarTokens(await cuentasApi.login(datos));
    try { const perfil = await cuentasApi.perfil(); setUsuario(perfil); setError(''); }
    catch (err) { borrarTokens(); throw err; }
  }

  return <AuthContext.Provider value={{ usuario, setUsuario, cargando, error, cargarSesion, iniciarSesion, cerrarSesion }}>{children}</AuthContext.Provider>;
}

// Este contexto comparte solamente la sesión. Los datos de cada página se consultan allí.
export function useAuth() { return useContext(AuthContext); }
