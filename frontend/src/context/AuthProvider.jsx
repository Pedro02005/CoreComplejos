import { useEffect, useState } from 'react';
import { borrarTokens, cuentasApi, guardarTokens, obtenerTokens } from '../services/api';
import { AuthContext } from './AuthContext.js';

export function AuthProvider({ children }) {
  // El perfil se recupera al recargar; la contraseña nunca se guarda en el navegador.
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  function cerrarSesion() {
    borrarTokens();
    setUsuario(null);
    setError('');
  }

  async function cargarSesion() {
    setCargando(true);
    setError('');
    if (!obtenerTokens()?.access) {
      setCargando(false);
      return;
    }
    try {
      setUsuario(await cuentasApi.perfil());
    } catch (err) {
      if (obtenerTokens()) setError(err.message);
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    cargarSesion();
    window.addEventListener('sesion-vencida', cerrarSesion);
    return () => window.removeEventListener('sesion-vencida', cerrarSesion);
  }, []);

  async function iniciarSesion(datos) {
    guardarTokens(await cuentasApi.login(datos));
    try {
      const perfil = await cuentasApi.perfil();
      setUsuario(perfil);
      setError('');
    } catch (err) {
      borrarTokens();
      throw err;
    }
  }

  return (
    <AuthContext.Provider
      value={{ usuario, setUsuario, cargando, error, cargarSesion, iniciarSesion, cerrarSesion }}
    >
      {children}
    </AuthContext.Provider>
  );
}

