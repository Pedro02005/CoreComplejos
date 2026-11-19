import { createContext, useContext } from 'react';

// Se separa el contexto de su componente para mantener estable la sesión al editar páginas.
export const AuthContext = createContext(null);

export function useAuth() {
  return useContext(AuthContext);
}
