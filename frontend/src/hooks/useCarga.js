import { useEffect, useState } from 'react';

// Carga datos al abrir una página o cambiar sus filtros. Ignora respuestas de páginas cerradas.
export function useCarga(cargar, dependencias = []) {
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    let activo = true;
    setCargando(true);
    setError('');
    Promise.resolve()
      .then(cargar)
      .then((resultado) => {
        if (activo) setDatos(resultado);
      })
      .catch((err) => {
        if (activo) setError(err.message);
      })
      .finally(() => {
        if (activo) setCargando(false);
      });
    return () => {
      activo = false;
    };
  }, [...dependencias, intento]);

  return { datos, cargando, error, recargar: () => setIntento((valor) => valor + 1) };
}
